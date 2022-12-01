import logging

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger(__name__)


def get_name(driver):
    profile_name = driver.find_element(By.ID, "user")

    return profile_name


def launch_test():
    options = Options()
    options.page_load_strategy = 'normal'
    options.add_experimental_option("detach", True)
    driver = webdriver.Chrome(options=options)
    try:
        driver.get("http://localhost:8000")
    except Exception as e:
        logger.info("\n\nTesting failed to launch because the server is not running", e)

    return driver


def logout(driver):
    driver.get("http://localhost:8000/accounts/logout")
    driver.get("https://accounts.google.com/logout")
    driver.get("http://localhost:8000")
    driver.quit()


def login(driver, element):
    try:
        login_button = WebDriverWait(driver, timeout=5).until(lambda d: driver.find_element(By.ID, element.strip()))
        login_button.click()
        return 1
    except Exception as e:
        logger.error('Login test error', e)
        return 0


def dashboard(params, driver):
    login(driver, 'login')
    google_button = WebDriverWait(driver, timeout=5).until(lambda d: driver.find_element(By.ID, "google_signin_btn"))
    google_button.click()
    login_input = driver.find_element(By.ID, 'identifierId')
    login_name = params['username']
    login_input.send_keys(login_name)
    next_btn = driver.find_element(By.ID, 'identifierNext')
    next_btn.click()
    password_input = WebDriverWait(driver, timeout=15).until(lambda d: driver.find_element(By.NAME, 'password'))
    password = params['password']
    pwd_next = None
    try:
        password_input.send_keys(password)
        next_btn = 'passwordNext'
        pwd_next = WebDriverWait(driver, timeout=10). \
            until(lambda d: driver.find_element(By.ID, next_btn))
    except Exception:
        logout(driver)
    try:
        webdriver.ActionChains(driver).move_to_element(pwd_next).click(pwd_next).perform()
    except Exception:
        logout(driver)
