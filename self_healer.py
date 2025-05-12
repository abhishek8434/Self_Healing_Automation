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
        # Create a simplified key structure
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
        # Determine element type from existing locators
        element_type = "input" if any("input" in str(loc["value"]).lower() for loc in locators.get("fallbacks", [])) else "button"
        
        example_json = '{"type": "css selector", "value": "' + ("input[type=\"text\"]" if element_type == "input" else "button[type=\"submit\"]") + '"}'  
        
        prompt = f"""Analyze this webpage and suggest working locators for a {element_type} element.
    Previous failed attempts: {locators}
    
    Return ONLY a JSON object in this exact format (use double quotes and escape inner quotes with \\) WITHOUT any line breaks or extra spaces:
    {example_json}
    
    Suggest robust locators like:
    - CSS: {element_type}[type=\"text\"], .{element_type}-field
    - XPath: //{element_type}[@type='text'], //{element_type}[contains(@class,'field')]"""

        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=300  # Increase this to capture more context
            )
            suggestion = response.choices[0].message.content.strip()

            # Parse and validate the suggestion
            suggested_locator = json.loads(suggestion)
            if 'type' in suggested_locator and 'value' in suggested_locator:
                locator_type = self._convert_locator_type(suggested_locator['type'])
                if locator_type:
                    print(f"[INFO] Trying AI suggested locator: {suggested_locator}")
                    element = self.driver.find_element(locator_type, suggested_locator['value'])
                    
                    # Save the successful locator
                    locator_key = self._get_locator_key(locators)
                    self.ai_locators.setdefault(locator_key, []).append({
                        'type': suggested_locator['type'],
                        'value': suggested_locator['value'],
                        'success': True,
                        'timestamp': str(datetime.datetime.now())
                    })
                    self._save_ai_locators()
                    return element
                else:
                    print(f"[WARNING] Unknown locator type: {suggested_locator['type']}")
            else:
                print(f"[WARNING] AI suggestion missing 'type' or 'value': {suggested_locator}")

        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse AI suggestion: {e}")
        except Exception as e:
            print(f"[ERROR] AI healing attempt failed: {e}")

        raise NoSuchElementException("Element not found even after AI healing attempt.")

    def _convert_locator_type(self, locator_type):
        return {
            'css selector': By.CSS_SELECTOR,
            'xpath': By.XPATH,
            'id': By.ID,
            'name': By.NAME,
            'class name': By.CLASS_NAME,
            'tag name': By.TAG_NAME,
            'link text': By.LINK_TEXT,
            'partial link text': By.PARTIAL_LINK_TEXT,
            'css': By.CSS_SELECTOR,
            'xpath expression': By.XPATH
        }.get(locator_type.lower().strip(), None)
