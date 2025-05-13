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

    def _ai_heal(self, locators: Dict) -> object:
        page_source = self.driver.page_source
        current_url = self.driver.current_url

        # Determine field type and context
        field_info = self._get_field_info(locators)
        
        # Extract relevant HTML context with more details
        html_context = self._get_enhanced_context()
        
        prompt = f"""Analyze this login page and find the submit button, ignoring any previous locator attempts.
            Page context: {html_context}

            Provide simple, reliable locators in this order:
            1. Basic button locators (type='submit')
            2. Text-based locators ('Submit', 'Login')
            3. Common class patterns ('submit-btn', 'login-button')
            """

        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a locator generator. Only respond with valid JSON arrays containing locator objects with 'type' and 'value' fields."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower temperature for more consistent JSON formatting
                max_tokens=500
            )
            
            # Clean and validate the response
            response_text = response.choices[0].message.content.strip()
            if not response_text.startswith('[') or not response_text.endswith(']'):
                raise json.JSONDecodeError("Invalid JSON format", response_text, 0)
                
            suggestions = json.loads(response_text)
            
            if not isinstance(suggestions, list):
                raise json.JSONDecodeError("Response is not a JSON array", response_text, 0)

            # Try each suggested locator
            for suggestion in suggestions:
                try:
                    if not isinstance(suggestion, dict) or 'type' not in suggestion or 'value' not in suggestion:
                        log_warning(f"Invalid locator format in suggestion: {suggestion}")
                        continue

                    locator_type = self._convert_locator_type(suggestion['type'])
                    if not locator_type:
                        log_warning(f"Unknown locator type: {suggestion['type']}")
                        continue

                    log_info(f"Trying AI suggested locator: {suggestion}")
                    element = self._find_with_retry({
                        'type': locator_type,
                        'value': suggestion['value']
                    })

                    if element:
                        # Save successful locator
                        locator_key = self._get_locator_key(locators)
                        self.ai_locators.setdefault(locator_key, []).append({
                            'type': suggestion['type'],
                            'value': suggestion['value'],
                            'success': True,
                            'timestamp': datetime.datetime.now().isoformat(),
                            'url': current_url
                        })
                        self._save_ai_locators()
                        return element

                except Exception as e:
                    log_warning(f"Failed to use suggested locator: {suggestion}, Error: {e}")
                    continue

        except json.JSONDecodeError as e:
            log_error(f"Failed to parse AI suggestions: {e}")
            log_error(f"Raw response: {response.choices[0].message.content if 'response' in locals() else 'No response'}")
        except Exception as e:
            log_error(f"AI healing attempt failed: {e}")

        # Cleanup old locators periodically
        self._cleanup_old_locators()
        
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

    def _get_field_info(self, locators: Dict) -> Dict:
            # Initialize default values
            field_info = {
                'type': 'input',  # Default to input
                'input_type': 'text',  # Default to text
                'name': '',
                'label': '',
                'placeholder': '',
                'context': ''
            }
    

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
