import pandas as pd
import time
import random
from playwright.sync_api import sync_playwright

EMAIL = "your_email"
PASSWORD = "your_password"

CSV_FILE = "products.csv"

def random_delay(a=3, b=6):
    time.sleep(random.uniform(a, b))

def login_facebook(page):
    print("Logging in...")
    page.goto("https://www.facebook.com/login")

    page.fill("#email", EMAIL)
    page.fill("#pass", PASSWORD)
    page.click("button[name='login']")

    page.wait_for_timeout(6000)

def post_marketplace(page, product):
    print("Posting:", product["title"])

    page.goto("https://www.facebook.com/marketplace/create/item")
    page.wait_for_timeout(5000)

    # Upload image
    page.set_input_files("input[type=file]", product["image_path"])
    random_delay()

    # Fill title
    page.fill("input[aria-label='Title']", product["title"])
    random_delay()

    # Fill price
    page.fill("input[aria-label='Price']", str(product["price"]))
    random_delay()

    # Fill description
    page.fill("textarea", product["description"])
    random_delay()

    # Next
    page.click("div[aria-label='Next']")
    page.wait_for_timeout(3000)

    # Publish
    page.click("div[aria-label='Publish']")
    page.wait_for_timeout(5000)

    print("Posted:", product["title"])

def main():
    df = pd.read_csv(CSV_FILE)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        login_facebook(page)

        for _, row in df.iterrows():
            try:
                post_marketplace(page, row)
                random_delay(8, 15)
            except Exception as e:
                print("ERROR:", row["title"], str(e))
                continue

        browser.close()

if __name__ == "__main__":
    main()
