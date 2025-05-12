# self_healer.py

import os
import json
from openai import OpenAI
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from dotenv import load_dotenv
import datetime

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class SelfHealer:
    def __init__(self, driver):
        self.driver = driver
        self.ai_locators_file = "ai_locators.json"
        self._load_ai_locators()

    def _load_ai_locators(self):
        try:
            if os.path.exists(self.ai_locators_file):
                with open(self.ai_locators_file, 'r') as f:
                    self.ai_locators = json.load(f)
            else:
                self.ai_locators = {}
        except Exception as e:
            print(f"[WARNING] Could not load AI locators: {e}")
            self.ai_locators = {}

    def _save_ai_locators(self):
        try:
            with open(self.ai_locators_file, 'w') as f:
                json.dump(self.ai_locators, f, indent=2)
        except Exception as e:
            print(f"[WARNING] Could not save AI locators: {e}")

    def _get_locator_key(self, locators):
        # Create a unique key based on the failed locators
        return json.dumps(locators, sort_keys=True)

    def find_element(self, locators):
        # Try primary locator first
        primary = locators.get("primary")
        try:
            return self._find(primary)
        except NoSuchElementException:
            print(f"[WARNING] Primary locator failed: {primary}")

        # Try fallback locators
        for fallback in locators.get("fallbacks", []):
            try:
                print(f"[INFO] Trying fallback: {fallback}")
                return self._find(fallback)
            except NoSuchElementException:
                print(f"[WARNING] Fallback locator failed: {fallback}")

        # Check if we have a saved AI locator for this scenario
        locator_key = self._get_locator_key(locators)
        if locator_key in self.ai_locators:
            saved_locators = self.ai_locators[locator_key]
            # Try each saved locator, starting with successful ones
            successful_locators = [loc for loc in saved_locators if loc.get('success', False)]
            all_locators = successful_locators + [loc for loc in saved_locators if not loc.get('success', False)]
            
            for saved_locator in all_locators:
                try:
                    print(f"[INFO] Trying saved AI locator: {saved_locator}")
                    locator = {
                        'type': saved_locator['type'],
                        'value': saved_locator['value']
                    }
                    return self._find(locator)
                except NoSuchElementException:
                    print(f"[WARNING] Saved AI locator failed: {saved_locator}")
                    continue

        # Use AI-powered recovery as last resort
        return self._ai_heal(locators)

    def _find(self, locator):
        locator_type = locator["type"]
        locator_value = locator["value"]
        
        return self.driver.find_element(locator_type, locator_value)

    def _ai_heal(self, locators):
        # Use OpenAI API to suggest a better locator
        example_json = '{"type": "css selector", "value": "button[type=\"submit\"]"}'  # Use escaped double quotes
        prompt = f"""Analyze this webpage and suggest working locators for a button element.
Previous failed attempts: {locators}

Return ONLY a JSON object in this exact format (use double quotes and escape inner quotes with \\) WITHOUT any line breaks or extra spaces:
{example_json}

Suggest robust locators like:
- CSS: button[type=\"submit\"], .login-button, .btn-primary
- XPath: //button[contains(@class,\"submit\")], //input[@type=\"submit\"]"""

        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=150
            )
            suggestion = response.choices[0].message.content.strip()
            print(f"[INFO] AI Suggestion: {suggestion}")
            
            # Parse and try the AI suggestion
            try:
                # Clean up the suggestion but preserve necessary spaces
                suggestion = ' '.join(suggestion.split())  # Normalize spaces instead of removing them
                if suggestion.startswith("{") and suggestion.endswith("}"):
                    # Replace single quotes with escaped double quotes
                    suggestion = suggestion.replace("'", '"')
                
                suggested_locator = json.loads(suggestion)
                if isinstance(suggested_locator, dict) and 'type' in suggested_locator and 'value' in suggested_locator:
                    print(f"[INFO] Trying AI suggested locator: {suggested_locator}")
                    # Convert string locator type to Selenium By class
                    locator_type = {
                        'css selector': By.CSS_SELECTOR,
                        'css': By.CSS_SELECTOR,  # Add alias
                        'xpath': By.XPATH,
                        'id': By.ID,
                        'name': By.NAME,
                        'class name': By.CLASS_NAME,
                        'tag name': By.TAG_NAME,
                        'link text': By.LINK_TEXT,
                        'partial link text': By.PARTIAL_LINK_TEXT
                    }.get(suggested_locator['type'].lower().strip())
                    
                    if locator_type:
                        # Save the suggestion before trying it
                        locator_key = self._get_locator_key(locators)
                        if locator_key not in self.ai_locators:
                            self.ai_locators[locator_key] = []
                        
                        # Try multiple alternative locators
                        alternative_locators = [
                            {'type': 'css selector', 'value': 'button[type="submit"]'},
                            {'type': 'css selector', 'value': '.btn-primary'},
                            {'type': 'xpath', 'value': '//button[contains(text(),"Submit")]'},
                            {'type': 'xpath', 'value': '//input[@type="submit"]'},
                            # Add the AI suggested locator as well
                            {'type': locator_type, 'value': suggested_locator['value']}
                        ]
                        
                        for alt_locator in alternative_locators:
                            try:
                                print(f"[INFO] Trying alternative locator: {alt_locator}")
                                element = self._find(alt_locator)
                                # Mark as successful if element is found
                                new_suggestion = {
                                    'type': alt_locator['type'],
                                    'value': alt_locator['value'],
                                    'success': True,
                                    'timestamp': str(datetime.datetime.now())
                                }
                                self.ai_locators[locator_key].append(new_suggestion)
                                self._save_ai_locators()
                                return element
                            except NoSuchElementException:
                                print(f"[WARNING] Alternative locator failed: {alt_locator}")
                                # Save the failed attempt too
                                new_suggestion = {
                                    'type': alt_locator['type'],
                                    'value': alt_locator['value'],
                                    'success': False,
                                    'timestamp': str(datetime.datetime.now())
                                }
                                self.ai_locators[locator_key].append(new_suggestion)
                                self._save_ai_locators()
                                continue
                    else:
                        print(f"[WARNING] Unknown locator type: {suggested_locator['type']}")
            except (json.JSONDecodeError, KeyError) as e:
                print(f"[WARNING] Could not parse AI suggestion: {e}")
                
        except Exception as e:
            print(f"[WARNING] AI healing attempt failed: {e}")
        
        raise NoSuchElementException("Element not found even after trying multiple AI healing strategies.")
