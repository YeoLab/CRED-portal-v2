import logging

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from .test_utils import dashboard, logout, launch_test

logger = logging.getLogger(__name__)


driver = launch_test()


def test_profile(params):
    dashboard(params, driver)
    profile = WebDriverWait(driver, timeout=10).until(lambda d: driver.find_element(By.ID, "profile"))
    webdriver.ActionChains(driver).move_to_element(profile).click(profile).perform()
    page_title = driver.find_element(By.ID, "profile_title")
    assert page_title.text == 'Profile'


def test_profile_edit():
    lab = 'Yeo Lab'
    institute = 'UCSD'
    lab_text = WebDriverWait(driver, timeout=5).until(lambda d: driver.find_element(By.ID, "id_lab"))
    inst_text = WebDriverWait(driver, timeout=5).until(lambda d: driver.find_element(By.ID, "id_institution"))
    lab_text.clear()
    inst_text.clear()
    inst_text.send_keys(institute)
    lab_text.send_keys(lab)
    submit = WebDriverWait(driver, timeout=5).until(lambda d: driver.find_element(By.XPATH, '/html/body/div/form/button'))
    webdriver.ActionChains(driver).move_to_element(submit).click(submit).perform()
    lab_text = WebDriverWait(driver, timeout=5).until(lambda d: driver.find_element(By.ID, "id_lab"))
    inst_text = WebDriverWait(driver, timeout=5).until(lambda d: driver.find_element(By.ID, "id_institution"))
    assert lab_text.text != lab
    assert inst_text != institute
    lab_text.clear()
    inst_text.clear()
    lab = 'SLAC'
    lab_text.send_keys(lab)
    institute = 'Accelerobio'
    inst_text.send_keys(institute)
    submit = WebDriverWait(driver, timeout=5).until(
        lambda d: driver.find_element(By.XPATH, '/html/body/div/form/button'))
    webdriver.ActionChains(driver).move_to_element(submit).click(submit).perform()
    logout(driver)
