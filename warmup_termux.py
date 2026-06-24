#!/usr/bin/env python3
"""
Zeta Warmup - Termux Edition
Reddit HTTP-based warmup script (no Playwright, no browser needed)
Works directly on Termux/Android with native IP.
"""
import os
import sys
import json
import time
import random
import requests
from datetime import datetime
from pathlib import Path

# Load .env if exists
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

# ── Config ──────────────────────────────────────────────────────────────────
USERNAME   = os.environ.get("REDDIT_USERNAME", "")
PASSWORD   = os.environ.get("REDDIT_PASSWORD", "")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

SUBREDDITS = [
    "AskReddit", "funny", "pics", "todayilearned",
    "mildlyinteresting", "worldnews", "science", "technology"
]
COMMENTS_PER_RUN = 3   # how many comments to post per run
UPVOTES_PER_RUN  = 10  # how many posts to upvote per run

WARMUP_COMMENTS = [
    "Great point! I've been thinking about this too.",
    "This is really interesting, thanks for sharing!",
    "I can relate to this. Well said!",
    "Thanks for the insight, very helpful!",
    "That's a fair take. Appreciate the perspective.",
    "Interesting! Never thought about it that way.",
    "Good observation. Thanks for bringing this up!",
    "I agree with this. Well explained!",
    "Nice one! Thanks for posting this.",
    "Very true! I've had similar experiences.",
    "This made my day, thanks!",
    "Solid point, couldn't agree more.",
    "Really appreciate you sharing this.",
    "This is exactly what I needed to read today.",
    "Totally underrated post. Deserves more attention.",
]

# ── Reddit HTTP Client ───────────────────────────────────────────────────────
class RedditClient:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": f"Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        })
        self.token = None
        self.logged_in = False

    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {msg}")

    def login(self) -> bool:
        """Login to Reddit and get access token."""
        self.log(f"Logging in as u/{self.username}...")
        try:
            # Step 1: Get initial cookies
            r = self.session.get("https://www.reddit.com/", timeout=15)
            time.sleep(2)

            # Step 2: Login via API
            login_data = {
                "username": self.username,
                "password": self.password,
                "dest": "https://www.reddit.com",
                "csrf_token": self._get_csrf_token(),
            }
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://www.reddit.com",
                "Referer": "https://www.reddit.com/login/",
                "X-Requested-With": "XMLHttpRequest",
            }
            r = self.session.post(
                "https://www.reddit.com/login",
                data=login_data,
                headers=headers,
                timeout=15
            )
            if r.status_code == 200:
                try:
                    data = r.json()
                    if data.get("dest") or "reddit.com" in str(data):
                        self.logged_in = True
                        self.log("✅ Login successful!")
                        return True
                except:
                    pass

            # Step 3: Try OAuth token approach
            return self._login_oauth()

        except Exception as e:
            self.log(f"❌ Login error: {e}")
            return self._login_oauth()

    def _get_csrf_token(self) -> str:
        """Extract CSRF token from Reddit cookies."""
        for cookie in self.session.cookies:
            if cookie.name == "csrf_token":
                return cookie.value
        return ""

    def _login_oauth(self) -> bool:
        """Login via Reddit OAuth2 with installed app client."""
        self.log("Trying OAuth2 login...")
        try:
            # Use Reddit's installed app client_id (public, no secret needed)
            # This is Reddit's own mobile app client_id - works without registration
            client_id = "ohXpoqrZYxa1ag"  # Reddit official iOS app
            
            auth = requests.auth.HTTPBasicAuth(client_id, "")
            data = {
                "grant_type": "password",
                "username": self.username,
                "password": self.password,
                "scope": "read submit vote identity",
            }
            headers = {
                "User-Agent": f"iOS:com.reddit.Reddit:2023.45.0 (by /u/{self.username})",
            }
            r = requests.post(
                "https://www.reddit.com/api/v1/access_token",
                auth=auth,
                data=data,
                headers=headers,
                timeout=15
            )
            if r.status_code == 200:
                result = r.json()
                if "access_token" in result:
                    self.token = result["access_token"]
                    self.session.headers.update({
                        "Authorization": f"bearer {self.token}",
                        "User-Agent": f"iOS:com.reddit.Reddit:2023.45.0 (by /u/{self.username})",
                    })
                    self.logged_in = True
                    self.log(f"✅ OAuth2 login successful! Token: {self.token[:20]}...")
                    return True
                else:
                    self.log(f"❌ OAuth2 failed: {result.get('error', 'unknown')}")
            else:
                self.log(f"❌ OAuth2 HTTP {r.status_code}: {r.text[:200]}")
        except Exception as e:
            self.log(f"❌ OAuth2 error: {e}")
        return False

    def get_hot_posts(self, subreddit: str, limit: int = 25) -> list:
        """Get hot posts from a subreddit."""
        try:
            url = f"https://oauth.reddit.com/r/{subreddit}/hot.json?limit={limit}"
            r = self.session.get(url, timeout=15)
            if r.status_code == 200:
                data = r.json()
                posts = data.get("data", {}).get("children", [])
                return [p["data"] for p in posts if not p["data"].get("locked") and not p["data"].get("archived")]
            else:
                self.log(f"⚠️ Could not fetch r/{subreddit}: HTTP {r.status_code}")
                return []
        except Exception as e:
            self.log(f"⚠️ Error fetching r/{subreddit}: {e}")
            return []

    def post_comment(self, post_id: str, text: str) -> bool:
        """Post a comment on a Reddit post."""
        try:
            url = "https://oauth.reddit.com/api/comment"
            data = {
                "api_type": "json",
                "thing_id": f"t3_{post_id}",
                "text": text,
            }
            r = self.session.post(url, data=data, timeout=15)
            if r.status_code == 200:
                result = r.json()
                errors = result.get("json", {}).get("errors", [])
                if not errors:
                    return True
                else:
                    self.log(f"⚠️ Comment errors: {errors}")
                    return False
            else:
                self.log(f"⚠️ Comment HTTP {r.status_code}: {r.text[:200]}")
                return False
        except Exception as e:
            self.log(f"⚠️ Comment error: {e}")
            return False

    def upvote(self, post_id: str) -> bool:
        """Upvote a Reddit post."""
        try:
            url = "https://oauth.reddit.com/api/vote"
            data = {
                "id": f"t3_{post_id}",
                "dir": "1",
            }
            r = self.session.post(url, data=data, timeout=15)
            return r.status_code == 200
        except:
            return False

    def get_karma(self) -> dict:
        """Get current karma stats."""
        try:
            r = self.session.get("https://oauth.reddit.com/api/v1/me", timeout=15)
            if r.status_code == 200:
                data = r.json()
                return {
                    "link_karma": data.get("link_karma", 0),
                    "comment_karma": data.get("comment_karma", 0),
                    "total_karma": data.get("total_karma", 0),
                }
        except:
            pass
        return {}


# ── Gemini AI Comment Generator ─────────────────────────────────────────────
def generate_comment_with_gemini(post_title: str, subreddit: str) -> str:
    """Generate a natural comment using Gemini AI."""
    if not GEMINI_KEY:
        return random.choice(WARMUP_COMMENTS)
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"""You are a regular Reddit user browsing r/{subreddit}.
Write a SHORT, natural, friendly comment (1-2 sentences max) for this post:
"{post_title}"

Rules:
- Sound like a real human, not a bot
- Be genuine and relevant to the post
- No hashtags, no emojis, no marketing
- Keep it casual and conversational
- Just the comment text, nothing else"""
        response = model.generate_content(prompt)
        comment = response.text.strip()
        if len(comment) > 300:
            comment = comment[:300]
        return comment
    except Exception as e:
        return random.choice(WARMUP_COMMENTS)


# ── Main Warmup Logic ────────────────────────────────────────────────────────
def run_warmup():
    print()
    print("=" * 60)
    print("  Zeta Warmup - Termux Edition")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  User: u/{USERNAME}")
    print("=" * 60)
    print()

    if not USERNAME or not PASSWORD:
        print("❌ ERROR: REDDIT_USERNAME and REDDIT_PASSWORD not set!")
        print("   Edit ~/alfa-agent/.env and add your credentials.")
        sys.exit(1)

    client = RedditClient(USERNAME, PASSWORD)

    # Login
    if not client.login():
        print("❌ Login failed. Check credentials.")
        sys.exit(1)

    # Get karma before
    karma_before = client.get_karma()
    if karma_before:
        print(f"📊 Karma before: {karma_before.get('total_karma', '?')} total")

    comments_posted = 0
    upvotes_done = 0
    subreddits_visited = []

    # Shuffle subreddits for variety
    subs = SUBREDDITS.copy()
    random.shuffle(subs)

    for subreddit in subs:
        if comments_posted >= COMMENTS_PER_RUN and upvotes_done >= UPVOTES_PER_RUN:
            break

        print(f"\n📌 Visiting r/{subreddit}...")
        posts = client.get_hot_posts(subreddit, limit=20)

        if not posts:
            print(f"   ⚠️ No posts found, skipping...")
            continue

        subreddits_visited.append(subreddit)
        print(f"   Found {len(posts)} posts")

        # Upvote some posts
        for post in posts[:3]:
            if upvotes_done >= UPVOTES_PER_RUN:
                break
            if client.upvote(post["id"]):
                upvotes_done += 1
                print(f"   👍 Upvoted: {post['title'][:60]}...")
                time.sleep(random.uniform(1, 3))

        # Post a comment
        if comments_posted < COMMENTS_PER_RUN:
            # Pick a post to comment on (not too new, not too old)
            eligible = [p for p in posts if p.get("num_comments", 0) > 5 and not p.get("locked")]
            if eligible:
                post = random.choice(eligible[:10])
                comment_text = generate_comment_with_gemini(post["title"], subreddit)
                print(f"   💬 Commenting on: {post['title'][:60]}...")
                print(f"   📝 Comment: {comment_text}")
                if client.post_comment(post["id"], comment_text):
                    comments_posted += 1
                    print(f"   ✅ Comment posted! ({comments_posted}/{COMMENTS_PER_RUN})")
                else:
                    print(f"   ❌ Comment failed")
                time.sleep(random.uniform(5, 10))

        # Human-like delay between subreddits
        time.sleep(random.uniform(3, 8))

    # Get karma after
    karma_after = client.get_karma()

    print()
    print("=" * 60)
    print("  Warmup Complete!")
    print(f"  Subreddits visited: {len(subreddits_visited)}")
    print(f"  Comments posted: {comments_posted}")
    print(f"  Upvotes given: {upvotes_done}")
    if karma_after:
        print(f"  Karma now: {karma_after.get('total_karma', '?')} total")
    print("=" * 60)
    print()

    return comments_posted > 0 or upvotes_done > 0


if __name__ == "__main__":
    success = run_warmup()
    sys.exit(0 if success else 1)
