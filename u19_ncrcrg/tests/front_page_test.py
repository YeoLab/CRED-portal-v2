import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from .test_utils import launch_test

logger = logging.getLogger(__name__)

driver = launch_test()


def test_frontpage_auth():
    elements = ['login', 'analyze', 'share', 'upload', 'submit_job', 'dashboard', 'manage_share']
    for element in elements:
        login(element)
        auth_select = WebDriverWait(driver, timeout=5).until(lambda d: driver.find_element(By.ID, "existing_org"))
        assert auth_select
        driver.back()


def test_frontpage_nonauth():
    elements = ['about', 'meta_data', 'toolkit']
    for element in elements:
        login(element)
        auth_select = WebDriverWait(driver, timeout=5).until(lambda d: driver.find_element(By.ID, "_dash-config"))
        assert auth_select
    driver.close()


def login(element):
    try:
        login_button = WebDriverWait(driver, timeout=5).until(lambda d: driver.find_element(By.ID, element.strip()))
        login_button.click()
        return 1
    except Exception as e:
        logger.error('Login test error', e)
        return 0
