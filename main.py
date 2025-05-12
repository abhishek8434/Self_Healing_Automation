# main.py

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from locators import Locators
from self_healer import SelfHealer
import logging
import time

logging.basicConfig(level=logging.INFO)

def main():
    driver = webdriver.Chrome()
    
    driver.get("https://practicetestautomation.com/practice-test-login/")
    
    healer = SelfHealer(driver)
    
    try:
        # Enter username
        username_field = healer.find_element(Locators.USERNAME_FIELD)
        if username_field:
            username_field.send_keys("student")
            logging.info("Entered username successfully.")

        # Enter password
        password_field = healer.find_element(Locators.PASSWORD_FIELD)
        if password_field:
            password_field.send_keys("Password123")
            logging.info("Entered password successfully.")

        # Click login button
        login_button = healer.find_element(Locators.LOGIN_BUTTON)
        if login_button:
            login_button.click()
            logging.info("Login button clicked successfully.")

        # Validate successful login
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        success_message = driver.find_element(By.TAG_NAME, "h1").text
        if "Logged In Successfully" in success_message:
            logging.info("Login successful!")
        else:
            logging.error("Login failed. Check credentials or element locators.")
        time.sleep(2)
        
    except Exception as e:
        try:
            logging.error(f"[ERROR] Failed to find and click the login button: {e}")
        except Exception as e:
            logging.error(f"[ERROR] Failed to find and click the login button: {e}")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()

