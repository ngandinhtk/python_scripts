import asyncio
import random
import re
import subprocess
import json
from models import Video
from config import Config
from rich.console import Console

console = Console()

class TikTokScraper:
    def __init__(self, proxy: str = None):
        self.proxy = proxy
        self.user_agent = random.choice(Config.USER_AGENTS)

    async def get_trending_videos(self, limit: int, min_views: int, min_likes: int):
        # Use #trending hashtag as a proxy for trending content since the official
        # trending API requires complex request signing (X-Bogus, msToken).
        console.log("Fetching trending videos from TikTok (via #trending)...")
        return await self.search_by_hashtag("trending", limit, min_views, min_likes)

    def _parse_count(self, text: str) -> int:
        """Converts strings like '1.2M' or '10K' to integers."""
        text = text.strip().upper()
        if not text:
            return 0
        
        multiplier = 1
        if text.endswith('K'):
            multiplier = 1000
            text = text[:-1]
        elif text.endswith('M'):
            multiplier = 1_000_000
            text = text[:-1]
        elif text.endswith('B'):
            multiplier = 1_000_000_000
            text = text[:-1]
        
        try:
            return int(float(text) * multiplier)
        except ValueError:
            return 0

    async def search_by_hashtag(self, hashtag: str, limit: int, min_views: int, min_likes: int):
        """Search for TikTok videos by hashtag using yt-dlp"""
        console.log(f"[yellow]Searching TikTok hashtag: #{hashtag} (using yt-dlp)...[/yellow]")
        
        videos_data = []
        try:
            url = f"https://www.tiktok.com/tag/{hashtag}"
            
            def fetch_videos():
                """Fetch video info using yt-dlp"""
                try:
                    ydl_opts = {
                        'quiet': False,
                        'no_warnings': False,
                        'extract_flat': 'in_playlist',  # Get playlist of videos without downloading
                        'playlistend': limit * 3,  # Get extra to filter
                        'user_agent': self.user_agent,
                        'socket_timeout': 30,
                        'http_headers': {
                            'Referer': 'https://www.tiktok.com/',
                        },
                    }
                    if self.proxy:
                        ydl_opts['proxy'] = self.proxy
                    
                    import yt_dlp
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        console.log(f"[dim]Extracting info from {url}...[/dim]")
                        info = ydl.extract_info(url, download=False)
                        return info
                except Exception as e:
                    console.log(f"[red]Error with yt-dlp approach: {str(e)[:100]}[/red]")
                    return None
            
            loop = asyncio.get_running_loop()
            info = await loop.run_in_executor(None, fetch_videos)
            
            if info and 'entries' in info:
                console.log(f"[dim]Found {len(info['entries'])} videos from yt-dlp[/dim]")
                
                for idx, entry in enumerate(info['entries'][:limit * 2]):  # Get extra to filter
                    try:
                        if isinstance(entry, dict):
                            title = entry.get('title', 'No Title')
                            url_video = entry.get('url') or entry.get('webpage_url')
                            author = entry.get('uploader', 'Unknown')
                            
                            if not url_video:
                                continue
                            
                            # Initialize with available data
                            videos_data.append(Video(
                                url=url_video,
                                title=title or 'No Title',
                                author=author or 'Unknown',
                                views=entry.get('view_count', 0) or 0,
                                likes=entry.get('like_count', 0) or 0,
                                comments=entry.get('comment_count', 0) or 0,
                                shares=0,  # yt-dlp usually doesn't provide share count
                                engagement_rate=0.0
                            ))
                    except Exception as e:
                        console.log(f"[dim]Warning parsing video {idx}: {str(e)[:50]}[/dim]")
                        continue
                
                console.log(f"[green]Extracted {len(videos_data)} videos using yt-dlp[/green]")
            else:
                console.log("[yellow]yt-dlp approach returned no entries. Falling back to Playwright...[/yellow]")
                return await self._search_by_hashtag_playwright(hashtag, limit, min_views, min_likes)
        
        except Exception as e:
            console.log(f"[yellow]yt-dlp search failed: {str(e)[:100]}. Falling back to Playwright...[/yellow]")
            return await self._search_by_hashtag_playwright(hashtag, limit, min_views, min_likes)
        
        # Filter by minimum requirements
        filtered_videos = [
            video for video in videos_data
            if video.views >= min_views and video.likes >= min_likes
        ]
        
        console.log(f"[dim]Filtered: {len(videos_data)} → {len(filtered_videos)} after applying filters[/dim]")
        return filtered_videos[:limit]

    async def _search_by_hashtag_playwright(self, hashtag: str, limit: int, min_views: int, min_likes: int):
        from playwright.async_api import async_playwright
        
        videos_data = []
        console.log(f"[yellow]Starting Playwright fallback for #{hashtag}...[/yellow]")
        
        async with async_playwright() as p:
            # Launch browser (headless=True is faster but easier to detect; try False if this fails)
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(user_agent=self.user_agent)
            page = await context.new_page()
            
            try:
                url = f"https://www.tiktok.com/tag/{hashtag}"
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                # Wait for video grid
                try:
                    await page.wait_for_selector('[data-e2e="search_video-item"]', timeout=10000)
                except:
                    console.log("[red]Could not find video elements on page via Playwright.[/red]")
                    return []

                # Extract candidates from grid
                elements = await page.locator('[data-e2e="search_video-item"]').all()
                console.log(f"[dim]Found {len(elements)} videos on grid. Checking details...[/dim]")
                
                for el in elements[:limit + 5]: # Check a few extra
                    if len(videos_data) >= limit:
                        break
                        
                    try:
                        link_el = el.locator('a').first
                        video_url = await link_el.get_attribute('href')
                        
                        if not video_url:
                            continue
                        if not video_url.startswith('http'):
                            video_url = f"https://www.tiktok.com{video_url}"
                        
                        # Get views from grid to pre-filter
                        views = 0
                        if await el.locator('[data-e2e="video-views"]').count() > 0:
                            views_str = await el.locator('[data-e2e="video-views"]').inner_text()
                            views = self._parse_count(views_str)
                        
                        if views < min_views:
                            continue
                            
                        # Visit video page to get Likes (Grid usually doesn't show likes)
                        # Note: This is slower but necessary for accurate like count filtering
                        new_page = await context.new_page()
                        await new_page.goto(video_url, wait_until="domcontentloaded", timeout=20000)
                        
                        likes = 0
                        try:
                            await new_page.wait_for_selector('[data-e2e="like-count"]', timeout=5000)
                            likes_str = await new_page.locator('[data-e2e="like-count"]').inner_text()
                            likes = self._parse_count(likes_str)
                        except:
                            pass
                        
                        await new_page.close()

                        if likes >= min_likes:
                            videos_data.append(Video(
                                url=video_url,
                                title=f"Video by {hashtag}", # Title extraction is complex on mobile view
                                author="Unknown",
                                views=views,
                                likes=likes,
                                comments=0,
                                shares=0,
                                engagement_rate=0.0
                            ))
                            console.log(f"[green]Found match: {likes} likes[/green]")
                    except Exception as e:
                        continue
            finally:
                await browser.close()
                
        return videos_data

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
                    'Referer': 'https://www.tiktok.com/',
                },
                'proxy': self.proxy,
            }
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            except Exception as e:
                # Log error but don't crash the bot
                console.log(f"[red]Failed to download {url}: {e}[/red]")

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _download)
