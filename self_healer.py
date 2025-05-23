# self_healer.py

import os
import json
from openai import OpenAI
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from dotenv import load_dotenv
import datetime
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils import log_info, log_warning, log_error
from typing import Dict, List, Optional

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class SelfHealer:
    def __init__(self, driver, max_retries: int = 3, retry_delay: int = 1):
        self.driver = driver
        self.ai_locators_file = "ai_locators.json"
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._load_ai_locators()

    def _load_ai_locators(self) -> None:
        try:
            if os.path.exists(self.ai_locators_file):
                with open(self.ai_locators_file, 'r') as f:
                    self.ai_locators = json.load(f)
            else:
                self.ai_locators = {}
        except Exception as e:
            log_warning(f"Could not load AI locators: {e}")
            self.ai_locators = {}

    def _save_ai_locators(self) -> None:
        try:
            with open(self.ai_locators_file, 'w') as f:
                json.dump(self.ai_locators, f, indent=2)
        except Exception as e:
            log_warning(f"Could not save AI locators: {e}")

    def _get_locator_key(self, locators: Dict) -> str:
        key_data = {
            "primary": {
                "type": str(locators["primary"]["type"]).lower(),
                "value": locators["primary"]["value"]
            },
            "fallbacks": [{
                "type": str(fb["type"]).lower(),
                "value": fb["value"]
            } for fb in locators.get("fallbacks", [])]
        }
        return json.dumps(key_data, sort_keys=True)

    def _cleanup_old_locators(self, days: int = 30) -> None:
        """Remove locators older than specified days."""
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
        for key in list(self.ai_locators.keys()):
            self.ai_locators[key] = [
                loc for loc in self.ai_locators[key]
                if datetime.datetime.fromisoformat(loc['timestamp']) > cutoff_date
            ]
            if not self.ai_locators[key]:
                del self.ai_locators[key]

    def find_element(self, locators: Dict, timeout: int = 10) -> Optional[object]:
        def _try_find_with_wait(loc: Dict) -> Optional[object]:
            try:
                return WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((loc["type"], loc["value"]))
                )
            except (TimeoutException, NoSuchElementException):
                return None
            except Exception as e:
                log_error(f"Unexpected error finding element: {e}")
                return None

        # Try primary locator
        primary = locators.get("primary")
        element = _try_find_with_wait(primary)
        if element:
            return element
        log_warning(f"Primary locator failed: {primary}")

        # Try fallbacks
        for fallback in locators.get("fallbacks", []):
            element = _try_find_with_wait(fallback)
            if element:
                return element
            log_warning(f"Fallback locator failed: {fallback}")

        # Try saved AI locators
        locator_key = self._get_locator_key(locators)
        if locator_key in self.ai_locators:
            saved_locators = self.ai_locators[locator_key]
            successful_locators = [loc for loc in saved_locators if loc.get('success', False)]
            all_locators = successful_locators + [loc for loc in saved_locators if not loc.get('success', False)]
            
            for saved_locator in all_locators:
                try:
                    log_info(f"Trying saved AI locator: {saved_locator}")
                    locator = {
                        'type': saved_locator['type'],
                        'value': saved_locator['value']
                    }
                    element = self._find_with_retry(locator)
                    if element:
                        return element
                except Exception as e:
                    log_warning(f"Saved AI locator failed: {saved_locator}, Error: {e}")
                    continue

        # AI healing as last resort
        return self._ai_heal(locators)

    def _find_with_retry(self, locator: Dict, max_retries: int = None) -> Optional[object]:
        """Find element with retry mechanism and iframe support."""
        retries = 0
        max_retries = max_retries or self.max_retries

        while retries < max_retries:
            try:
                # Try finding in main content
                element = self._find(locator)
                if element and element.is_displayed():
                    return element

                # Try finding in iframes
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                for iframe in iframes:
                    try:
                        self.driver.switch_to.frame(iframe)
                        element = self._find(locator)
                        if element and element.is_displayed():
                            return element
                    except Exception as e:
                        log_warning(f"Error searching in iframe: {e}")
                    finally:
                        self.driver.switch_to.default_content()

            except StaleElementReferenceException:
                log_warning(f"Stale element, retry {retries + 1}/{max_retries}")
            except Exception as e:
                log_error(f"Error finding element: {e}")
                break

            retries += 1
            if retries < max_retries:
                time.sleep(self.retry_delay)

        return None

    def _find(self, locator: Dict) -> object:
        """Enhanced element finding with explicit waits."""
        try:
            return WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((locator["type"], locator["value"]))
            )
        except TimeoutException:
            # Try alternative strategies
            try:
                # Try with case-insensitive contains for text
                if "text()" in str(locator["value"]):
                    modified_xpath = locator["value"].replace(
                        "text()", "translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')"
                    )
                    return self.driver.find_element(locator["type"], modified_xpath)
                # Try partial match for input fields
                elif locator["type"] == By.NAME or locator["type"] == By.ID:
                    return self.driver.find_element(By.XPATH, 
                        f"//*[contains(@{locator['type']}, '{locator['value']}')]")
            except:
                pass
            return self.driver.find_element(locator["type"], locator["value"])

    def _get_field_info(self, locators: Dict) -> Dict:
        field_info = {
            'type': 'unknown',
            'input_type': 'unknown',
            'context': ''
        }
        
        # Analyze primary and fallback locators
        all_locators = [locators['primary']] + locators.get('fallbacks', [])
        for loc in all_locators:
            value = str(loc['value']).lower()
            
            # Check for button/submit indicators
            if any(x in value for x in ['button', 'submit', 'login', 'sign in']):
                field_info['type'] = 'button'
                field_info['input_type'] = 'submit'
                break
            
            # Check for username/email indicators
            elif any(x in value for x in ['user', 'email', 'login']):
                field_info['type'] = 'input'
                field_info['input_type'] = 'text'
                break
            
            # Check for password indicators
            elif 'password' in value:
                field_info['type'] = 'input'
                field_info['input_type'] = 'password'
                break
        
        # Get surrounding context
        try:
            field_info['context'] = self._analyze_page_context()
        except:
            pass
        
        return field_info

    def _ai_heal(self, locators: Dict) -> object:
        page_source = self.driver.page_source
        current_url = self.driver.current_url

        # Determine field type and context
        field_info = self._get_field_info(locators)
        
        # Create field-specific prompts
        if field_info['type'] == 'input':
            if field_info['input_type'] == 'password':
                prompt = """Find the password input field on this login page. Look for:
                1. input[type='password']
                2. Common password field patterns (name='password', id contains 'password')
                3. Input field with password-related attributes"""
            else:  # username/email
                prompt = """Find the username/email input field on this login page. Look for:
                1. input[type='text'] or input[type='email']
                2. Common login field patterns (name/id contains 'username', 'email', 'login', 'user')
                3. First input field in the login form that's not password"""
        else:  # button
            prompt = """Find the submit/login button on this page. Look for:
                1. button[type='submit']
                2. input[type='submit']
                3. Button with text containing 'Login', 'Sign in', 'Submit'
                4. Common button classes ('login-btn', 'submit-button')"""

        # Add page context
        prompt += f"\nPage URL: {current_url}\nRelevant HTML context: {self._get_enhanced_context()}"

        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a locator generator. Respond with a JSON array of locator objects, each containing 'type' and 'value' fields. Start with the most specific locators."}, 
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            # Process response and try locators
            suggestions = json.loads(response.choices[0].message.content.strip())
            
            for suggestion in suggestions:
                try:
                    locator_type = self._convert_locator_type(suggestion['type'])
                    if not locator_type:
                        continue

                    log_info(f"Trying AI suggested locator: {suggestion}")
                    element = self._find_with_retry({
                        'type': locator_type,
                        'value': suggestion['value']
                    })

                    if element:
                        # Save successful locator
                        self._save_successful_locator(locators, suggestion, current_url)  # Fixed: using locators instead of original_locators
                        return element

                except Exception as e:
                    log_warning(f"Failed to use suggested locator: {suggestion}, Error: {e}")
                    continue

        except Exception as e:
            log_error(f"AI healing attempt failed: {e}")

        raise NoSuchElementException("Element not found even after AI healing attempt.")

    def _get_enhanced_context(self) -> str:
        # Get full page structure
        full_page = self.driver.page_source
        # Find all interactive elements
        elements = self.driver.find_elements(By.CSS_SELECTOR, "input, button, a[role='button']")
        # Get their attributes and surrounding HTML
        context = ""
        for elem in elements:
            context += elem.get_attribute("outerHTML") + "\n"
            # Get parent and sibling context
            parent = elem.find_element(By.XPATH, "..")
            context += parent.get_attribute("outerHTML") + "\n"
        return context

    def _convert_locator_type(self, locator_type: str) -> Optional[str]:
        """Convert string locator type to Selenium By class attribute."""
        return {
            'css selector': By.CSS_SELECTOR,
            'xpath': By.XPATH,
            'id': By.ID,
            'name': By.NAME,
            'class name': By.CLASS_NAME,
            'tag name': By.TAG_NAME,
            'link text': By.LINK_TEXT,
            'partial link text': By.PARTIAL_LINK_TEXT,
            'css': By.CSS_SELECTOR,  # alias
            'xpath expression': By.XPATH  # alias
        }.get(locator_type.lower().strip())

    def _save_successful_locator(self, original_locators: Dict, successful_locator: Dict, current_url: str) -> None:
        """Save a successful AI-suggested locator for future use."""
        try:
            locator_key = self._get_locator_key(original_locators)
            
            # Create new locator entry
            new_locator = {
                'type': successful_locator['type'],
                'value': successful_locator['value'],
                'success': True,
                'timestamp': datetime.datetime.now().isoformat(),
                'url': current_url
            }
            
            # Add to existing locators or create new entry
            if locator_key in self.ai_locators:
                # Check if this locator already exists
                exists = any(
                    loc['type'] == successful_locator['type'] and 
                    loc['value'] == successful_locator['value']
                    for loc in self.ai_locators[locator_key]
                )
                if not exists:
                    self.ai_locators[locator_key].append(new_locator)
            else:
                self.ai_locators[locator_key] = [new_locator]
            
            # Save to file
            self._save_ai_locators()
            
        except Exception as e:
            log_warning(f"Failed to save successful locator: {e}")

    def _smart_retry(self, locator: Dict, context: str = None) -> Optional[object]:
        # Add smart retry logic with dynamic delay
        base_delay = self.retry_delay
        for attempt in range(self.max_retries):
            try:
                # Try different strategies based on previous failures
                if attempt == 1:
                    # Try with relaxed matching
                    modified_locator = self._relax_locator_constraints(locator)
                    element = self._find(modified_locator)
                elif attempt == 2:
                    # Try with parent context
                    element = self._find_with_parent_context(locator)
                else:
                    element = self._find(locator)
                    
                if element and element.is_displayed():
                    return element
                    
            except Exception as e:
                log_warning(f"Attempt {attempt + 1} failed: {e}")
                time.sleep(base_delay * (attempt + 1))  # Exponential backoff
        return None

    def _find_by_visual_attributes(self, element_type: str, context: Dict) -> Optional[object]:
        """Find elements using visual attributes like position and appearance."""
        try:
            # Get viewport dimensions
            viewport_width = self.driver.execute_script("return window.innerWidth;")
            viewport_height = self.driver.execute_script("return window.innerHeight;")
            
            # Find elements in the expected region
            if element_type == 'submit_button':
                # Usually at the bottom of forms
                xpath = f"//button[contains(@class, 'submit') and position() > {viewport_height/2}]"
                return self.driver.find_element(By.XPATH, xpath)
                
            return None
        except Exception as e:
            log_warning(f"Visual detection failed: {e}")
            return None

    def _generate_dynamic_locators(self, element_type: str, context: Dict) -> List[Dict]:
        """Generate dynamic locators based on element type and context."""
        locators = []
        if element_type == 'input':
            # Generate semantic locators
            locators.extend([
                {"type": By.CSS_SELECTOR, "value": f"input[type='{context.get('input_type', 'text')}']:not([hidden])"},
                {"type": By.CSS_SELECTOR, "value": f"input[placeholder*='{context.get('placeholder', '')}' i]"},
                {"type": By.XPATH, "value": f"//input[contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{context.get('label', '').lower()}')]"},
            ])
        return locators

    def _optimize_locator_search(self, locators: List[Dict]) -> List[Dict]:
        """Optimize locator search order based on historical success rates."""
        if not hasattr(self, '_locator_stats'):
            self._locator_stats = {}
        
        def get_score(locator):
            key = f"{locator['type']}:{locator['value']}"
            stats = self._locator_stats.get(key, {'success': 0, 'total': 0})
            if stats['total'] == 0:
                return 0
            return stats['success'] / stats['total']
        
        return sorted(locators, key=get_score, reverse=True)

    def _update_locator_model(self, successful_locator: Dict, context: Dict) -> None:
        """Update the ML model with successful locator patterns."""
        if not hasattr(self, '_locator_patterns'):
            self._locator_patterns = []
        
        pattern = {
            'locator': successful_locator,
            'context': context,
            'timestamp': datetime.datetime.now().isoformat()
        }
        self._locator_patterns.append(pattern)
        
        # Periodically train the model
        if len(self._locator_patterns) >= 100:
            self._train_locator_model()

    def _load_healing_config(self) -> Dict:
        """Load healing configuration from file."""
        config_file = "healing_config.json"
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            log_warning(f"Could not load healing config: {e}")
        
        return {
            'max_retries': 3,
            'retry_delay': 1,
            'healing_strategies': ['relaxed_match', 'parent_context', 'visual_detection'],
            'ai_model_config': {
                'temperature': 0.3,
                'max_tokens': 150
            }
        }
