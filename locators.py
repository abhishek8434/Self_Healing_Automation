# locators.py
from selenium.webdriver.common.by import By

class Locators:
    LOGIN_BUTTON = {
        "primary": {"type": By.ID, "value": "submit"},
        "fallbacks": [
            {"type": By.CSS_SELECTOR, "value": "#submit"},
            {"type": By.XPATH, "value": "(//button[normalize-space()='Submit'])[1]"},
            {"type": By.NAME, "value": "submit"},
        ]
    }
