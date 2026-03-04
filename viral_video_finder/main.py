import argparse
import asyncio
import os
from config import Config
from tiktok_scraper import TikTokScraper
from douyin_scraper import DouyinScraper
from export import export_results
from rich.console import Console
from rich.table import Table

console = Console()

async def main():
    parser = argparse.ArgumentParser(description="Viral Video Finder CLI")
    parser.add_argument("--platform", type=str, choices=["tiktok", "douyin"], required=True,
                        help="Specify the platform to scrape (tiktok or douyin)")
    parser.add_argument("--hashtag", type=str,
                        help="Search for videos by hashtag (TikTok) or keyword/hashtag (Douyin)")
    parser.add_argument("--limit", type=int, default=Config.DEFAULT_LIMIT,
                        help=f"Number of videos to fetch (default: {Config.DEFAULT_LIMIT})")
    parser.add_argument("--min_views", type=int, default=Config.MIN_VIEWS,
                        help=f"Minimum view count for videos (default: {Config.MIN_VIEWS})")
    parser.add_argument("--min_likes", type=int, default=Config.MIN_LIKES,
                        help=f"Minimum like count for videos (default: {Config.MIN_LIKES})")
    parser.add_argument("--export_csv", type=str,
                        help="Export results to a CSV file (e.g., videos.csv)")
    parser.add_argument("--export_json", type=str,
                        help="Export results to a JSON file (e.g., videos.json)")
    parser.add_argument("--download", action="store_true",
                        help="Download the found videos")
    parser.add_argument("--output_dir", type=str, default=".",
                        help="Directory to save downloaded videos")
    parser.add_argument("--proxy", type=str,
                        help="Proxy URL (e.g., http://user:pass@host:port)")
    parser.add_argument("--cookies-file", type=str,
                        help="Path to a cookies file (e.g., cookies.txt). Required for Douyin.")

    args = parser.parse_args()

    scraper = None
    if args.platform == "tiktok":
        if args.cookies_file:
            console.log("[yellow]Warning: --cookies-file is ignored for TikTok scraping.[/yellow]")
        scraper = TikTokScraper(proxy=args.proxy)
    elif args.platform == "douyin":
        if not args.cookies_file:
            console.log("[bold red]Error: Douyin scraping requires a cookies file. Please provide one with --cookies-file.[/bold red]")
            return
        scraper = DouyinScraper(proxy=args.proxy, cookies_path=args.cookies_file)

    # Clean hashtag if provided (remove leading #)
    if args.hashtag and args.hashtag.startswith('#'):
        args.hashtag = args.hashtag.lstrip('#')

    search_type = f"hashtag: #{args.hashtag}" if args.hashtag else "trending"
    console.log(f"Scraping {args.platform.capitalize()} for {search_type} videos...")

    scraped_videos = []
    try:
        if args.hashtag:
            scraped_videos = await scraper.search_by_hashtag(
                hashtag=args.hashtag,
                limit=args.limit,
                min_views=args.min_views,
                min_likes=args.min_likes
            )
        else:
            scraped_videos = await scraper.get_trending_videos(
                limit=args.limit,
                min_views=args.min_views,
                min_likes=args.min_likes
            )
    except Exception as e:
        console.log(f"[bold red]An error occurred during scraping: {e}[/bold red]")
        return

    if scraped_videos:
        console.log(f"Found {len(scraped_videos)} viral videos.")
        table = Table(title="Viral Videos Found")
        table.add_column("Author", style="cyan", no_wrap=True)
        table.add_column("Title", style="magenta")
        table.add_column("Views", justify="right", style="green")
        table.add_column("Likes", justify="right", style="green")
        table.add_column("Engagement", justify="right", style="yellow")
        table.add_column("URL", style="blue", overflow="fold")

        for video in scraped_videos:
            table.add_row(
                video.author, video.title, f"{video.views:,}", f"{video.likes:,}",
                f"{video.engagement_rate:.2%}", video.url
            )
        console.print(table)

        if args.export_csv:
            export_results(scraped_videos, args.export_csv, "csv")
            console.log(f"Exported {len(scraped_videos)} videos to {args.export_csv}")
        if args.export_json:
            export_results(scraped_videos, args.export_json, "json")
            console.log(f"Exported {len(scraped_videos)} videos to {args.export_json}")

        if args.download:
            console.log(f"Downloading {len(scraped_videos)} videos...")
            if args.output_dir != ".":
                os.makedirs(args.output_dir, exist_ok=True)

            for video in scraped_videos:
                await scraper.download_video(video.url, output_path=args.output_dir)
                # Policy: Add a delay between downloads to avoid rate limiting (politeness)
                await asyncio.sleep(Config.DOWNLOAD_DELAY)
            console.log("Download complete.")
    else:
        console.log("\n[yellow]No viral videos found matching the specified criteria.[/yellow]")
        console.log("This could be because:")
        console.log(f"  • No videos under the hashtag met the thresholds (Views > {args.min_views:,}, Likes > {args.min_likes:,}).")
        console.log("  • The platform is rate-limiting your requests or its API has changed.")
        if args.platform == "douyin":
            console.log("  • For Douyin, your cookies file might be expired or invalid.")
        console.log("\n[bold]Suggestion:[/bold] Try running with [green]--min_views 0 --min_likes 0[/green] to see if ANY videos are being found.")
        console.log("If you see '0 views' in the debug logs, the platform layout may have changed. Check selectors in scraper files.")

if __name__ == "__main__":
    asyncio.run(main())
