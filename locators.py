# locators.py
from selenium.webdriver.common.by import By

class Locators:
    USERNAME_FIELD = {
        "primary": {"type": By.ID, "value": "username1"},
        "fallbacks": [
            {"type": By.CSS_SELECTOR, "value": "#username1"},
            {"type": By.XPATH, "value": "/html/body/div[1]/div/section/section/div[1]/div[1]/input1"},
            {"type": By.NAME, "value": "username1"},
        ]
    }
    PASSWORD_FIELD = {
            "primary": {"type": By.ID, "value": "password1"},
            "fallbacks": [
                {"type": By.CSS_SELECTOR, "value": "#password1"},
                {"type": By.XPATH, "value": "/html/body/div[1]/div/section/section/div[1]/div[2]/input1"},
                {"type": By.NAME, "value": "password1"},
        ]
    }
    LOGIN_BUTTON = {
        "primary": {"type": By.ID, "value": "submit1"},
        "fallbacks": [
            {"type": By.CSS_SELECTOR, "value": "#submit1"},
            {"type": By.XPATH, "value": "(//button[normalize-space()='Submit'])[2]"},
            {"type": By.NAME, "value": "submit1"},
        ]
    }
