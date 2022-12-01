import time

from selenium import webdriver
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from .test_utils import dashboard, logout, launch_test

driver = launch_test()


def test_collection(params):
    dashboard(params, driver)


def test_file_manager():
    job_btn = WebDriverWait(driver, timeout=50).until(lambda d: driver.find_element(By.ID, 'newJob'))
    job_btn.click()
    submit_job_title = WebDriverWait(driver, timeout=5).until(lambda d: driver.find_element(By.ID, "submitJobTitle"))
    assert submit_job_title.text == 'Process & Analyze Data'
    files_btn = driver.find_element(By.ID, 'selectFiles')
    files_btn.click()
    files_mgr_title = WebDriverWait(driver, timeout=5) \
        .until(lambda d: driver.find_element(By.ID, 'pane1-collection-label'))
    assert files_mgr_title.text == 'Collection'
    collection = WebDriverWait(driver, timeout=5).until(
        lambda d: driver.find_element(By.LINK_TEXT, 'CReD Portal Dev Collection'))
    assert collection.text == "CReD Portal Dev Collection"


def test_upload_files():
    time.sleep(3)
    path_input = WebDriverWait(driver, timeout=15).until(lambda d: driver.find_element(By.ID, "pane1-path-input"))
    path = "raw_files/cr-test-1/cellranger_count_3.0.2/"
    path_input.send_keys(path)
    path_input.send_keys(Keys.RETURN)


def test_selected_files():
    selected_ds = WebDriverWait(driver, timeout=15).until(
        lambda d: driver.find_element(By.XPATH, '//*[@id="pane1-directory"]/div/ul/li/div/div/button[1]'))
    selected_ds.click()
    submit_btn = WebDriverWait(driver, timeout=15).until(
        lambda d: driver.find_element(By.XPATH, '//*[@id="pane1-directory"]/form/div[2]/button'))
    submit_btn.click()


def test_submit_job():
    run_btn = WebDriverWait(driver, timeout=5).until(
        lambda d: driver.find_element(By.XPATH, "/html/body/div[2]/div[1]/div[3]/div/div/button[2]"))
    run_btn.click()
    job_name = "cr3-test-2"
    project_name = "Proteomics"
    sample_id = "2"
    job_summary = "Automated test"
    time.sleep(3)
    job_name_input = WebDriverWait(driver, timeout=5).until(
        lambda d: driver.find_elements(By.ID, "id_experiment_nickname"))
    job_name_input[1].send_keys(job_name)
    project_input = WebDriverWait(driver, timeout=5).until(
        lambda d: driver.find_elements(By.ID, "id_project"))
    project_input[1].clear()
    project_input[1].send_keys(project_name)
    sample_id_input = WebDriverWait(driver, timeout=5).until(
        lambda d: driver.find_elements(By.ID, "id_sample_id"))
    sample_id_input[0].send_keys(sample_id)
    job_sum_input = WebDriverWait(driver, timeout=5).until(
        lambda d: driver.find_elements(By.ID, "id_experiment_summary"))
    job_sum_input[1].send_keys(job_summary)

    try:
        driver.execute_script("window.scrollTo(100, 100000);")
    except Exception:
        driver.close()
    modal = None
    try:
        modal = WebDriverWait(driver, timeout=15).until(
            lambda d: driver.find_element(By.ID, "modal-CellrangerCount302Job"))
    except Exception:
        logout(driver)

    x = range(8)
    for n in x:
        modal.send_keys(Keys.ARROW_DOWN)
    submit = WebDriverWait(driver, timeout=15).until(
        lambda d: driver.find_elements(By.ID, "submit_job_ft"))
    webdriver.ActionChains(driver).move_to_element(submit[1]).click(submit[1]).perform()
    job_record = WebDriverWait(driver, timeout=15).until(
        lambda d: driver.find_elements(
            By.XPATH, '//*[@id="table"]/div[2]/div/div[2]/div[2]/table/tbody/tr[3]/td[1]'))
    job_record[0].click()
    logout(driver)


