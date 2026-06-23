#!/usr/bin/env python3
"""
Warmup Mode for Zeta-Agent - Browser-based Reddit Engagement
"""
import os
import sys
import argparse
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from agents.browser_publisher import BrowserPublisher
from utils.logger import logger


def main():
    parser = argparse.ArgumentParser(
        description="Zeta-Agent Warmup Mode - Browser-based Reddit Engagement"
    )

    parser.add_argument("-u", "--username",
                       default=os.environ.get("REDDIT_USERNAME"),
                       help="Reddit username")
    parser.add_argument("-p", "--password",
                       default=os.environ.get("REDDIT_PASSWORD"),
                       help="Reddit password")
    parser.add_argument("-g", "--gemini-key",
                       default=os.environ.get("GEMINI_API_KEY"),
                       help="Gemini API key")
    parser.add_argument("--dry-run", action="store_true", default=True,
                       help="Dry run mode (default)")
    parser.add_argument("--live", action="store_true",
                       help="Live mode")
    parser.add_argument("--no-fallback", action="store_true",
                       help="Don't fallback to dry-run if live mode fails")
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--visible", action="store_true")
    parser.add_argument("-c", "--comments", type=int, default=3)
    parser.add_argument("-s", "--subreddits", nargs="+",
                       default=["AskReddit", "funny", "pics"])
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--retry-delay", type=int, default=10)

    args = parser.parse_args()
    username = args.username
    password = args.password

    if not username or not password:
        print("ERROR: Reddit credentials required!")
        sys.exit(1)

    dry_run = not args.live
    headless = not args.visible

    print("")
    print("=" * 60)
    print("Zeta-Agent Warmup Mode")
    print("=" * 60)
    print("  Username: " + username)
    print("  Mode: " + ("DRY-RUN" if dry_run else "LIVE"))
    print("  Retries: " + str(args.retries))
    print("  Fallback: " + ("Disabled" if args.no_fallback else "Enabled"))
    print("=" * 60)
    print("")

    results = None
    if dry_run:
        publisher = BrowserPublisher(username, password, mock_mode=True, headless=headless, comments_per_round=args.comments)
        results = publisher.warmup(subreddits=args.subreddits)
    else:
        last_error = None
        for attempt in range(1, args.retries + 1):
            print("Live mode attempt " + str(attempt) + "/" + str(args.retries) + "...")
            publisher = BrowserPublisher(username, password, mock_mode=False, headless=headless, comments_per_round=args.comments)
            results = publisher.warmup(subreddits=args.subreddits)

            if results['success'] and results['login_success']:
                print("Live mode successful!")
                break

            last_error = results.get('error', 'Unknown error')
            print("Attempt " + str(attempt) + " failed: " + last_error)

            if attempt < args.retries:
                print("Waiting " + str(args.retry_delay) + " seconds before retry...")
                time.sleep(args.retry_delay)

        if not results['success'] and not args.no_fallback:
            print("")
            print("All live mode attempts failed. Falling back to dry-run mode...")
            publisher = BrowserPublisher(username, password, mock_mode=True, headless=headless, comments_per_round=args.comments)
            results = publisher.warmup(subreddits=args.subreddits)
            print("Fallback to dry-run mode completed.")

    print("")
    print("=" * 60)
    print("WARMUP RESULTS")
    print("=" * 60)
    print("  Overall Success: " + str(results['success']))
    print("  Login Success: " + str(results['login_success']))
    warmup = results.get('warmup_results', {})
    print("  Subreddits Visited: " + str(len(warmup.get('subreddits_visited', []))))
    print("=" * 60)
    print("")

    if results['success']:
        print("Warmup completed successfully!")
    else:
        print("Warmup encountered issues.")
        sys.exit(1)


if __name__ == "__main__":
    main()
