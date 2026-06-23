#!/usr/bin/env python3
"""
Warmup Mode for Zeta-Agent - Browser-based Reddit Engagement
============================================================

Uses Playwright browser automation with Residential Proxy support.

Required:
- REDDIT_USERNAME
- REDDIT_PASSWORD

Optional (for proxy):
- REDDIT_PROXY_SERVER - Proxy URL (e.g., "http://proxy.example.com:8080")
- REDDIT_PROXY_USERNAME - Proxy username
- REDDIT_PROXY_PASSWORD - Proxy password
"""
import os
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from agents.browser_publisher import BrowserPublisher


def main():
    parser = argparse.ArgumentParser(description="Zeta-Agent Warmup Mode")
    
    parser.add_argument("-u", "--username",
                       default=os.environ.get("REDDIT_USERNAME"),
                       help="Reddit username")
    parser.add_argument("-p", "--password",
                       default=os.environ.get("REDDIT_PASSWORD"),
                       help="Reddit password")
    parser.add_argument("-g", "--gemini-key",
                       default=os.environ.get("GEMINI_API_KEY"),
                       help="Gemini API key")
    parser.add_argument("--dry-run", action="store_true",
                       help="Dry run mode - simulate without posting")
    parser.add_argument("--live", action="store_true",
                       help="Live mode - actually post to Reddit")
    parser.add_argument("-c", "--comments", type=int, default=3,
                       help="Comments per subreddit")
    parser.add_argument("-s", "--subreddits", nargs="+",
                       default=["AskReddit", "funny", "pics", "todayilearned", "mildlyinteresting"],
                       help="Subreddits to warm up")

    args = parser.parse_args()

    if not args.username or not args.password:
        print("ERROR: REDDIT_USERNAME and REDDIT_PASSWORD required!")
        sys.exit(1)

    # Determine mode
    live_mode = args.live and not args.dry_run

    print("")
    print("=" * 60)
    print("Zeta-Agent Warmup Mode")
    print("=" * 60)
    print(f"  Username: {args.username}")
    print(f"  Mode: {'LIVE' if live_mode else 'DRY-RUN'}")
    print(f"  Comments: {args.comments} per subreddit")
    print(f"  Subreddits: {', '.join(args.subreddits)}")
    
    # Check for proxy
    proxy_server = os.environ.get("REDDIT_PROXY_SERVER")
    if proxy_server:
        print(f"  Proxy: {proxy_server}")
    
    print("=" * 60)
    print("")

    # Run warmup using browser publisher
    publisher = BrowserPublisher(
        username=args.username,
        password=args.password,
        mock_mode=not live_mode,  # mock_mode is opposite of live_mode
        headless=True,
        comments_per_round=args.comments,
        # Proxy settings from environment
        proxy_server=os.environ.get("REDDIT_PROXY_SERVER"),
        proxy_username=os.environ.get("REDDIT_PROXY_USERNAME"),
        proxy_password=os.environ.get("REDDIT_PROXY_PASSWORD")
    )

    results = publisher.warmup(subreddits=args.subreddits)

    # Exit with error code if failed
    if not results.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()
