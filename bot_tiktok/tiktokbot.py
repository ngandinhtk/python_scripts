import undetected_chromedriver as uc
import csv, time
from cookie_loader import load_cookies
from uploader import upload_video
from caption_ai import generate_caption
from config import POSTS_FILE, TIKTOK_UPLOAD_URL

driver = uc.Chrome()
driver.get("https://www.tiktok.com")
time.sleep(5)

load_cookies(driver)
driver.refresh()
time.sleep(5)

driver.get(TIKTOK_UPLOAD_URL)
time.sleep(5)

with open(POSTS_FILE, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)

    for row in reader:
        video_path = row["video_path"]
        caption = row["caption"]
        affiliate_link = row["affiliate_link"]

        if caption.strip() == "":
            caption = generate_caption(affiliate_link)

        upload_video(driver, video_path, caption)

driver.quit()
