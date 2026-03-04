"""Utility script to export cookies from Douyin/TikTok.

Run this script; it will open a browser window where you can log in manually.
After you finish logging in, close the browser (or press ENTER in the terminal) and the
script will write a `cookies.txt` file in Netscape format suitable for the scraper.

Usage:
    python export_cookies.py --platform douyin
    python export_cookies.py --platform tiktok

"""
import argparse
import asyncio
from playwright.async_api import async_playwright

async def export(platform: str, out_file: str = "cookies.txt"):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        url = "https://www.douyin.com" if platform == "douyin" else "https://www.tiktok.com"
        print(f"Navigate to {url} and log in. Close the browser or press ENTER when done.")
        await page.goto(url)
        # give user time to login
        input("Press ENTER after you have logged in and the page has fully loaded...")
        cookies = await context.cookies()
        # write Netscape format
        with open(out_file, "w", encoding="utf-8") as f:
            f.write("# Netscape HTTP Cookie File\n")
            for c in cookies:
                domain = c.get("domain", "")
                path = c.get("path", "/")
                secure = "TRUE" if c.get("secure") else "FALSE"
                http_only = "TRUE" if c.get("httpOnly") else "FALSE"
                expires = str(int(c.get("expires", 0)))
                name = c.get("name", "")
                value = c.get("value", "")
                f.write(f"{domain}\tTRUE\t{path}\t{secure}\t{expires}\t{name}\t{value}\n")
        print(f"Wrote {len(cookies)} cookies to {out_file}")
        await browser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export cookies from Douyin/TikTok using Playwright")
    parser.add_argument("--platform", choices=["douyin", "tiktok"], required=True)
    parser.add_argument("--output", default="cookies.txt", help="Output filename")
    args = parser.parse_args()
    asyncio.run(export(args.platform, args.output))
