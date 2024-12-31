import os
from selenium import webdriver

# Path to Geckodriver
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GECKODRIVER_PATH = os.path.join(BASE_DIR, "..", "geckodrivers", "geckodriver.exe")  # Move up one level

# Debugging
print(f"Resolved Geckodriver Path: {GECKODRIVER_PATH}")
if not os.path.exists(GECKODRIVER_PATH):
    print("Geckodriver not found at the specified path. Please verify the location.")
    exit(1)

try:
    # Initialize Firefox WebDriver with the Geckodriver path
    driver = webdriver.Firefox(executable_path=GECKODRIVER_PATH)
    driver.get("https://www.google.com")
    print("Firefox successfully launched!")
    driver.quit()
except Exception as e:
    print(f"Error: {e}")
