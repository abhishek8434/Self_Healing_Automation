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
    
    try:
        driver.get("https://practicetestautomation.com/practice-test-login/")
        # driver.get("https://practice.expandtesting.com/login")
        # driver.get("https://mrpdev.eatanceapp.com/backoffice/home")
        healer = SelfHealer(driver)
        
        # Enter username
        username_field = healer.find_element(Locators.USERNAME_FIELD)
        username_field.send_keys("student")
        # username_field.send_keys("practice")
        # username_field.send_keys("support@eatanceapp.com")
        logging.info("Entered username successfully.")

        # Enter password
        password_field = healer.find_element(Locators.PASSWORD_FIELD)
        password_field.send_keys("Password123")
        # password_field.send_keys("SuperSecretPassword!")
        # password_field.send_keys("Error@123")
        logging.info("Entered password successfully.")

        # Click login button
        login_button = healer.find_element(Locators.LOGIN_BUTTON)
        login_button.click()
        logging.info("Login button clicked successfully.")
        
        time.sleep(2)  # Give page time to load
        logging.info(f"Current URL: {driver.current_url}")  # Log the current URL
        logging.info(f"Page title: {driver.title}") # Wait for 2 seconds to observe the page after login

        # Validate successful login
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        success_message = driver.find_element(By.TAG_NAME, "h1").text
        logging.info(f"Found message: {success_message}")  # Add this line to see what text was found
        if "Logged In Successfully" in success_message:
            logging.info("Login successful!")
            time.sleep(3)
        else:
            logging.error("Login failed. Check credentials or element locators.")
            
    except Exception as e:
        logging.error(f"[ERROR] Test execution failed: {str(e)}")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    main()

