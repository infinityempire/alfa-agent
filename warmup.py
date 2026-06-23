#!/usr/bin/env python3
"""
Warmup Mode for Zeta-Agent - Browser-based Reddit Engagement
============================================================

A lightweight warmup script using Playwright browser automation.
Requires ONLY:
- REDDIT_USERNAME - Your Reddit username
- REDDIT_PASSWORD - Your Reddit password
- GEMINI_API_KEY - Optional Gemini API key for AI comments

Usage:
    python warmup.py                    # Dry-run mode (default)
    python warmup.py --live             # Live mode (posts comments)
    python warmup.py --username USER --password PASS
    python warmup.py --subreddits AskReddit funny pics
"""
import os
import sys
import asyncio
import argparse
from pathlib import Path
from typing import List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from agents.browser_publisher import BrowserPublisher
from utils.logger import logger


def main():
    """Main entry point for warmup mode."""
    parser = argparse.ArgumentParser(
        description="Zeta-Agent Warmup Mode - Browser-based Reddit Engagement",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python warmup.py                                    # Dry-run mode
  python warmup.py --live                            # Live mode
  python warmup.py -u Any_Run_914 -p "pass123"       # With credentials
  python warmup.py --subreddits AskReddit funny       # Custom subreddits

Required Environment Variables (or command line args):
  REDDIT_USERNAME - Reddit account username
  REDDIT_PASSWORD - Reddit account password
  GEMINI_API_KEY  - Optional Gemini API key for AI comments
        """
    )
    
    # Credential arguments
    parser.add_argument("-u", "--username", 
                       default=os.environ.get("REDDIT_USERNAME"),
                       help="Reddit username (or set REDDIT_USERNAME env var)")
    parser.add_argument("-p", "--password", 
                       default=os.environ.get("REDDIT_PASSWORD"),
                       help="Reddit password (or set REDDIT_PASSWORD env var)")
    parser.add_argument("-g", "--gemini-key",
                       default=os.environ.get("GEMINI_API_KEY"),
                       help="Gemini API key (optional, or set GEMINI_API_KEY env var)")
    
    # Mode arguments
    parser.add_argument("--dry-run", action="store_true", default=True,
                       help="Dry run mode - simulate without posting (default)")
    parser.add_argument("--live", action="store_true",
                       help="Live mode - actually post comments to Reddit")
    
    # Browser arguments
    parser.add_argument("--headless", action="store_true", default=True,
                       help="Run browser in headless mode (default)")
    parser.add_argument("--visible", action="store_true",
                       help="Run browser in visible mode")
    
    # Behavior arguments
    parser.add_argument("-c", "--comments", type=int, default=3,
                       help="Number of comments per warmup round (default: 3)")
    parser.add_argument("-s", "--subreddits", nargs="+",
                       default=["AskReddit", "funny", "pics", "todayilearned", "mildlyinteresting"],
                       help="Subreddits to warm up in")
    
    args = parser.parse_args()
    
    # Validate credentials
    username = args.username
    password = args.password
    
    if not username or not password:
        print("ERROR: Reddit credentials required!")
        print("  Set environment variables: REDDIT_USERNAME, REDDIT_PASSWORD")
        print("  Or provide via command line: --username USER --password PASS")
        print("\nExample:")
        print("  export REDDIT_USERNAME='Any_Run_914'")
        print("  export REDDIT_PASSWORD='[Dog7fr7es$#]'")
        print("  python warmup.py --live")
        sys.exit(1)
    
    # Determine mode
    dry_run = not args.live
    headless = not args.visible
    
    # Display configuration
    print("\n" + "=" * 60)
    print("Zeta-Agent Warmup Mode")
    print("=" * 60)
    print(f"  Username:     {username}")
    print(f"  Mode:        {'🧪 DRY-RUN' if dry_run else '🚀 LIVE'}")
    print(f"  Browser:     {'Headless' if headless else 'Visible'}")
    print(f"  Comments:    {args.comments} per round")
    print(f"  Subreddits:  {', '.join(args.subreddits)}")
    print(f"  Gemini AI:   {'Enabled' if args.gemini_key else 'Disabled'}")
    print("=" * 60 + "\n")
    
    # Create publisher and run warmup
    publisher = BrowserPublisher(
        username=username,
        password=password,
        mock_mode=dry_run,
        headless=headless,
        comments_per_round=args.comments
    )
    
    results = publisher.warmup(subreddits=args.subreddits)
    
    # Display results summary
    print("\n" + "=" * 60)
    print("WARMUP RESULTS")
    print("=" * 60)
    print(f"  Overall Success: {results['success']}")
    print(f"  Login Success:  {results['login_success']}")
    
    warmup = results.get('warmup_results', {})
    print(f"  Subreddits Visited: {len(warmup.get('subreddits_visited', []))}")
    print(f"  Posts Viewed:      {warmup.get('posts_viewed', 0)}")
    print(f"  Comments Posted:   {warmup.get('comments_posted', 0)}")
    print(f"  Mode:              {results.get('mode', 'unknown').upper()}")
    print("=" * 60 + "\n")
    
    if results['success']:
        print("✅ Warmup completed successfully!")
        print("   The account is now warmed up for engagement.")
    else:
        print("❌ Warmup encountered issues.")
        print("   Check the logs above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
