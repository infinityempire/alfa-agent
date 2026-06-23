#!/usr/bin/env python3
"""
Warmup Mode for Zeta-Agent - Reddit Engagement using PRAW API
============================================================

Uses Reddit's official API (PRAW) for reliable warmup without browser.
Requires ONLY:
- REDDIT_CLIENT_ID - Reddit app client ID
- REDDIT_CLIENT_SECRET - Reddit app client secret  
- REDDIT_USERNAME - Your Reddit username
- REDDIT_PASSWORD - Your Reddit password
- REDDIT_USER_AGENT - Reddit app user agent (e.g., "Zeta Warmup Bot")
"""
import os
import sys
import argparse
import time
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

import praw
from config.settings import REDDIT_CONFIG
from utils.logger import logger


# Warmup comments pool
WARMUP_COMMENTS = [
    "Great point! I've been thinking about this too.",
    "This is interesting, thanks for sharing!",
    "I can relate to this. Well said!",
    "Thanks for the insight!",
    "That's a fair take. Appreciate the perspective.",
    "Interesting! Never thought about it that way.",
    "Good observation. Thanks for bringing this up!",
    "I agree with this. Well explained!",
    "Nice one! Thanks for posting this.",
    "Very true! I've had similar experiences.",
]


def get_reddit_client():
    """Initialize Reddit client using PRAW."""
    client_id = os.environ.get("REDDIT_CLIENT_ID") or REDDIT_CONFIG.get("client_id")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET") or REDDIT_CONFIG.get("client_secret")
    username = os.environ.get("REDDIT_USERNAME") or REDDIT_CONFIG.get("username")
    password = os.environ.get("REDDIT_PASSWORD") or REDDIT_CONFIG.get("password")
    user_agent = os.environ.get("REDDIT_USER_AGENT") or "Zeta Warmup Bot/1.0"
    
    if not all([client_id, client_secret, username, password]):
        return None
        
    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
        username=username,
        password=password
    )


def browse_subreddit(reddit, subreddit_name, comments_per_subreddit):
    """Browse a subreddit and warmup by viewing and voting on posts."""
    try:
        subreddit = reddit.subreddit(subreddit_name)
        posts_viewed = 0
        
        for submission in subreddit.hot(limit=comments_per_subreddit * 3):
            try:
                if not submission.ups > 0:
                    submission.upvote()
            except:
                pass
            
            posts_viewed += 1
            time.sleep(random.uniform(1, 3))
        
        return posts_viewed
    except Exception as e:
        logger.warning(f"Error browsing r/{subreddit_name}: {e}")
        return 0


def post_comment(reddit, subreddit_name, comments_count):
    """Post warmup comments to a subreddit."""
    try:
        subreddit = reddit.subreddit(subreddit_name)
        comments_posted = 0
        
        for submission in subreddit.hot(limit=comments_count * 2):
            if comments_posted >= comments_count:
                break
                
            try:
                comment_text = random.choice(WARMUP_COMMENTS)
                submission.reply(comment_text)
                comments_posted += 1
                logger.info(f"Posted comment in r/{subreddit_name}: {comment_text[:50]}...")
                time.sleep(random.uniform(3, 8))
                
            except Exception as e:
                logger.warning(f"Error posting to {submission.id}: {e}")
                continue
        
        return comments_posted
    except Exception as e:
        logger.warning(f"Error posting to r/{subreddit_name}: {e}")
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="Zeta-Agent Warmup Mode - Reddit API Warmup"
    )

    parser.add_argument("-u", "--username",
                       default=os.environ.get("REDDIT_USERNAME"),
                       help="Reddit username")
    parser.add_argument("-p", "--password",
                       default=os.environ.get("REDDIT_PASSWORD"),
                       help="Reddit password")
    parser.add_argument("--client-id",
                       default=os.environ.get("REDDIT_CLIENT_ID"),
                       help="Reddit client ID")
    parser.add_argument("--client-secret",
                       default=os.environ.get("REDDIT_CLIENT_SECRET"),
                       help="Reddit client secret")
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

    has_api = bool(os.environ.get("REDDIT_CLIENT_ID") and os.environ.get("REDDIT_CLIENT_SECRET"))
    dry_run = args.dry_run or (not args.live and not has_api)

    print("")
    print("=" * 60)
    print("Zeta-Agent Warmup Mode (PRAW API)")
    print("=" * 60)
    print(f"  Username: {args.username or 'Not set'}")
    print(f"  Mode: {'LIVE' if not dry_run else 'DRY-RUN'}")
    print(f"  Comments: {args.comments} per subreddit")
    print(f"  Subreddits: {', '.join(args.subreddits)}")
    print("=" * 60)
    print("")

    if dry_run:
        print("DRY-RUN: Would perform warmup activities")
        print(f"  - Browse {args.comments} posts in each subreddit")
        print(f"  - Post {args.comments} comments per subreddit")
        print("")
        print("SUCCESS - Warmup completed in dry-run mode!")
        return

    reddit = get_reddit_client()
    if not reddit:
        print("ERROR: Reddit API credentials not configured!")
        print("")
        print("Please set these environment variables:")
        print("  REDDIT_CLIENT_ID=your_client_id")
        print("  REDDIT_CLIENT_SECRET=your_client_secret")
        print("  REDDIT_USERNAME=your_username")
        print("  REDDIT_PASSWORD=your_password")
        print("  REDDIT_USER_AGENT='Zeta Warmup Bot/1.0'")
        print("")
        print("Alternatively, add them to .env file or GitHub Secrets")
        sys.exit(1)

    try:
        user = reddit.user.me()
        print(f"Connected to Reddit as: {user.name}")
    except Exception as e:
        print(f"ERROR: Failed to connect to Reddit: {e}")
        sys.exit(1)

    total_subreddits = 0
    total_posts = 0
    total_comments = 0

    for subreddit_name in args.subreddits:
        print(f"\n--- Warming up r/{subreddit_name} ---")
        
        posts = browse_subreddit(reddit, subreddit_name, args.comments)
        total_posts += posts
        print(f"  Viewed/voted on {posts} posts")
        
        comments = post_comment(reddit, subreddit_name, args.comments)
        total_comments += comments
        print(f"  Posted {comments} comments")
        
        total_subreddits += 1

    print("")
    print("=" * 60)
    print("WARMUP RESULTS")
    print("=" * 60)
    print(f"  Subreddits visited: {total_subreddits}")
    print(f"  Posts viewed/voted: {total_posts}")
    print(f"  Comments posted: {total_comments}")
    print("=" * 60)
    print("")
    print("SUCCESS - Warmup completed!")


if __name__ == "__main__":
    main()
