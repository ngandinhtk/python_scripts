import time, random
from selenium.webdriver.common.by import By
from config import DELAY_MIN, DELAY_MAX

def upload_video(driver, video_path, caption):
    upload_input = driver.find_element(By.XPATH, '//input[@type="file"]')
    upload_input.send_keys(video_path)

    time.sleep(10)

    caption_box = driver.find_element(By.XPATH, '//textarea')
    caption_box.clear()
    caption_box.send_keys(caption)

    time.sleep(3)

    post_btn = driver.find_element(By.XPATH, '//button[contains(text(),"Post")]')
    post_btn.click()

    time.sleep(random.randint(DELAY_MIN, DELAY_MAX))
