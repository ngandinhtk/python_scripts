import undetected_chromedriver as uc
import time
from cookie_loader import load_cookies

def main():
    try:
        driver = uc.Chrome()
    except Exception as e:
        print(f"Lỗi khởi tạo Chrome: {e}")
        print("Đang thử cập nhật chromedriver...")
        driver = uc.Chrome(version_main=None)  # Tự động tải version phù hợp
    
    driver.get("https://www.tiktok.com")
    time.sleep(5)

    load_cookies(driver, "cookies.json")

    driver.refresh()
    time.sleep(10)

    print("Check if logged in manually. Press Enter to quit.")
    input()
    driver.quit()

if __name__ == "__main__":
    main()
