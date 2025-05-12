# locators.py
from selenium.webdriver.common.by import By

class Locators:
    USERNAME_FIELD = {
        "primary": {"type": By.ID, "value": "username"},
        "fallbacks": [
            {"type": By.CSS_SELECTOR, "value": "#username"},
            {"type": By.XPATH, "value": "/html/body/div[1]/div/section/section/div[1]/div[1]/input"},
            {"type": By.NAME, "value": "username"},
        ]
    }
    PASSWORD_FIELD = {
            "primary": {"type": By.ID, "value": "password"},
            "fallbacks": [
                {"type": By.CSS_SELECTOR, "value": "#password"},
                {"type": By.XPATH, "value": "/html/body/div[1]/div/section/section/div[1]/div[2]/input"},
                {"type": By.NAME, "value": "password"},
        ]
    }
    LOGIN_BUTTON = {
        "primary": {"type": By.ID, "value": "submit"},
        "fallbacks": [
            {"type": By.CSS_SELECTOR, "value": "#submit"},
            {"type": By.XPATH, "value": "(//button[normalize-space()='Submit'])[1]"},
            {"type": By.NAME, "value": "submit"},
        ]
    }
