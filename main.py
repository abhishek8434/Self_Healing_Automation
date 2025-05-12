# main.py

from selenium import webdriver
from selenium.webdriver.common.by import By
from locators import Locators
from self_healer import SelfHealer

def main():
    driver = webdriver.Chrome()
    driver.get("https://practicetestautomation.com/practice-test-login/")
    
    healer = SelfHealer(driver)
    
    # Attempt to find and click the login button
    try:
        login_button = healer.find_element(Locators.LOGIN_BUTTON)
        login_button.click()
        print("[INFO] Login button clicked successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to find and click the login button: {e}")

    driver.quit()

if __name__ == "__main__":
    main()
