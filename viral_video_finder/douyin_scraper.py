import asyncio
import random
import json
from models import Video
from config import Config
from rich.console import Console

console = Console()

class DouyinScraper:
    def __init__(self, proxy: str = None, cookies_path: str = None):
        self.proxy = proxy
        self.user_agent = random.choice(Config.USER_AGENTS)
        self.cookies_path = cookies_path

    async def get_trending_videos(self, limit: int, min_views: int, min_likes: int):
        # Use #trending hashtag as a proxy for trending content
        console.log("Fetching trending videos from Douyin (via #trending)...")
        return await self.search_by_hashtag("trending", limit, min_views, min_likes)

    def _parse_count(self, text: str) -> int:
        """Converts strings like '1.2W' (万) or '10K' to integers."""
        text = text.strip().upper()
        if not text:
            return 0
        
        multiplier = 1
        if 'W' in text or '万' in text:
            multiplier = 10000
            text = text.replace('W', '').replace('万', '')
        elif 'K' in text:
            multiplier = 1000
            text = text[:-1]
        
        try:
            return int(float(text) * multiplier)
        except ValueError:
            return 0

    async def search_by_hashtag(self, hashtag: str, limit: int, min_views: int, min_likes: int):
        console.log(f"Searching Douyin for hashtag '{hashtag}' using Playwright...")
        console.log("[yellow]Warning: Douyin selectors change frequently and may need to be updated in the code.[/yellow]")
        console.log("[yellow]Warning: View counts are not available on Douyin search pages. Filtering by --min_views will likely yield no results.[/yellow]")
        from playwright.async_api import async_playwright

        videos_data = []
        partial_videos = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, proxy={'server': self.proxy} if self.proxy else None)
            
            context = await browser.new_context(user_agent=self.user_agent)
            if self.cookies_path:
                try:
                    console.log(f"Attempting to load cookies from {self.cookies_path}")
                    with open(self.cookies_path, 'r') as f:
                        cookies = json.load(f)
                    await context.add_cookies(cookies)
                    console.log("[green]Successfully loaded cookies.[/green]")
                except FileNotFoundError:
                    console.log(f"[red]Error: Cookies file not found at '{self.cookies_path}'[/red]")
                    await browser.close()
                    return []
                except json.JSONDecodeError:
                    console.log(f"[red]Error: Could not decode JSON from '{self.cookies_path}'. Ensure it is a valid JSON cookie file.[/red]")
                    await browser.close()
                    return []
                except Exception as e:
                    console.log(f"[red]An unexpected error occurred while loading cookies: {e}[/red]")
                    await browser.close()
                    return []

            page = await context.new_page()
            try:
                # Douyin uses a search page for hashtags
                await page.goto(f"https://www.douyin.com/search/{hashtag}?type=video", wait_until="networkidle", timeout=60000)

                console.log("Scraping initial video list from search page...")
                # TODO: VERIFY DOUYIN SELECTORS. These are placeholders and will likely need updating.
                video_selector = 'div[data-e2e="search-video-list"] li > div'
                console.log(f"[dim]Using selector for video list: '{video_selector}'[/dim]")

                for _ in range(5): # Scroll a few times to load results
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(2000)

                video_elements = await page.locator(video_selector).all()
                console.log(f"[dim]Debug: Found {len(video_elements)} potential video elements on page.[/dim]")

                if not video_elements:
                    console.log("[bold red]Error: Could not find any video elements on the page.[/bold red]")
                    console.log("[bold red]The Douyin website structure has likely changed. The 'video_selector' in 'douyin_scraper.py' needs to be updated.[/bold red]")

                for item in video_elements[:int(limit * 1.5)] :
                    try:
                        # TODO: VERIFY DOUYIN SELECTORS
                        url_element = item.locator('a').first
                        url = await url_element.get_attribute('href')
                        if url and not url.startswith('http'):
                            url = f"https:{url}"

                        title_element = item.locator('img[class*="content-image"]').first
                        title = await title_element.get_attribute('alt')

                        if url:
                            partial_videos.append({"url": url, "title": title, "author": "Unknown", "views": 0})
                    except Exception as e:
                        console.log(f"[dim]Debug: Could not parse a video item, skipping. Error: {e}[/dim]")
                        continue
                
                console.log(f"Fetching detailed metadata for {len(partial_videos)} videos. This may take a while...")
                for i, video_info in enumerate(partial_videos):
                    try:
                        console.log(f"  ({i+1}/{len(partial_videos)}) Scraping: {video_info['url']}")
                        await page.goto(video_info['url'], wait_until="networkidle", timeout=30000)
                        
                        # TODO: VERIFY DOUYIN SELECTORS for stats on the video page
                        author = await page.locator('p[class*="author-name"]').inner_text()
                        likes_text = await page.locator('span[class*="like-count"]').inner_text()
                        comments_text = await page.locator('span[class*="comment-count"]').inner_text()
                        shares_text = await page.locator('span[class*="share-count"]').inner_text()

                        # Views are often not directly displayed; this is a placeholder
                        views = 0
                        likes = self._parse_count(likes_text)
                        comments = self._parse_count(comments_text)
                        shares = self._parse_count(shares_text)

                        videos_data.append(Video(
                            url=video_info['url'],
                            title=video_info['title'] or 'No Title',
                            author=author.strip() or 'Unknown',
                            views=views,
                            likes=likes,
                            shares=shares,
                            comments=comments,
                            engagement_rate=0.0, # Cannot be calculated without views
                            description=video_info['title']
                        ))
                    except Exception as e:
                        console.log(f"[yellow]Warning: Could not fetch details for {video_info['url']}. Error: {e}[/yellow]")
                        continue
            except Exception as e:
                console.log(f"[red]An error occurred during Playwright scraping on Douyin: {e}[/red]")
            finally:
                await browser.close()

        filtered_videos = [
            video for video in videos_data
            # Allow videos with 0 views to pass if extraction failed, provided they meet like criteria
            if (video.views >= min_views or video.views == 0) and video.likes >= min_likes
        ]
        console.log(f"[dim]Debug: {len(videos_data)} videos processed. {len(filtered_videos)} matched filters.[/dim]")
        return filtered_videos[:limit]

    async def download_video(self, url: str, output_path: str = "."):
        """Downloads a video using yt-dlp."""
        import yt_dlp

        console.log(f"Downloading {url}...")

        def _download():
            ydl_opts = {
                'outtmpl': f'{output_path}/%(title)s [%(id)s].%(ext)s',
                'quiet': True,
                'no_warnings': True,
                'user_agent': self.user_agent,
                'http_headers': {
                    'Referer': 'https://www.douyin.com/',
                },
                'proxy': self.proxy,
                'cookiefile': self.cookies_path,
            }
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            except Exception as e:
                # Log error but don't crash the bot
                console.log(f"[red]Failed to download {url}: {e}[/red]")

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _download)
