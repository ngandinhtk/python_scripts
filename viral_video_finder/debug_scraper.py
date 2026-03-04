#!/usr/bin/env python3
"""Debug script to inspect TikTok page structure"""

import asyncio
from playwright.async_api import async_playwright
import json

async def debug_tiktok():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()
        
        # Go to TikTok hashtag page
        print("Loading TikTok hashtag page...")
        await page.goto("https://www.tiktok.com/tag/trending", timeout=60000)
        print("Page loaded, waiting for content...")
        
        # Wait and scroll
        await page.wait_for_timeout(5000)
        await page.evaluate("window.scrollBy(0, 2000);")
        await page.wait_for_timeout(2000)
        
        print("\n=== PAGE STRUCTURE ANALYSIS ===\n")
        
        # Check all links
        all_links = await page.locator('a').all()
        print(f"Total links on page: {len(all_links)}")
        
        # Check video links specifically
        video_links = await page.locator('a[href*="/video/"]').all()
        print(f"Video links found: {len(video_links)}")
        
        if video_links:
            print("\nFirst 5 video link hrefs:")
            for i, link in enumerate(video_links[:5]):
                href = await link.get_attribute('href')
                print(f"  {i+1}. {href}")
        
        # Try JavaScript extraction
        print("\n=== JAVASCRIPT EXTRACTION ===\n")
        try:
            data = await page.evaluate("""
                () => {
                    const videoLinks = Array.from(document.querySelectorAll('a[href*="/video/"]'))
                        .map(l => l.href)
                        .slice(0, 5);
                    return videoLinks;
                }
            """)
            print(f"JavaScript found {len(data)} video links:")
            for link in data:
                print(f"  - {link}")
        except Exception as e:
            print(f"JavaScript extraction failed: {e}")
        
        # Save full HTML for inspection
        html = await page.content()
        with open("debug_full_page.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("\n✓ Full page HTML saved to debug_full_page.html")
        
        # Check page title and meta
        title = await page.title()
        print(f"\nPage title: {title}")
        
        # Check if page has video containers with different patterns
        patterns = [
            ('div[data-testid*="video"]', 'data-testid video'),
            ('div[class*="VideoItem"]', 'VideoItem class'),
            ('div[class*="video"]', 'video class (broad)'),
            ('article', 'article tags'),
            ('[data-e2e*="video"]', 'data-e2e video'),
        ]
        
        print("\n=== CONTAINER SEARCH ===\n")
        for selector, desc in patterns:
            try:
                elements = await page.locator(selector).all()
                print(f"{desc}: {len(elements)} elements found")
            except:
                print(f"{desc}: selector failed")
        
        await browser.close()
        print("\n✓ Debug complete!")

if __name__ == "__main__":
    asyncio.run(debug_tiktok())
