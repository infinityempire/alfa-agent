#!/usr/bin/env python3
"""
Zeta Warmup - Termux Edition v2
Reddit session-based warmup (no OAuth2, no Playwright, no App needed)
Works directly on Termux/Android with native IP.
"""
import os, sys, re, json, time, random, requests
from datetime import datetime

# ── Load credentials from env vars ──────────────────────────────────────────
USERNAME   = os.environ.get("REDDIT_USERNAME", "")
PASSWORD   = os.environ.get("REDDIT_PASSWORD", "")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

SUBREDDITS = [
    "AskReddit", "funny", "pics", "todayilearned",
    "mildlyinteresting", "worldnews", "science", "technology"
]
COMMENTS_PER_RUN = 3
UPVOTES_PER_RUN  = 8

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
]

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# ── Reddit Session Login ─────────────────────────────────────────────────────
def reddit_login(username, password):
    """Login to Reddit using old.reddit.com session API."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36",
        "Accept": "application/json, text/html",
        "Accept-Language": "en-US,en;q=0.9",
    })

    log(f"Connecting to Reddit...")
    try:
        # Step 1: Visit login page to get cookies
        r = s.get("https://old.reddit.com/login", timeout=20)
        time.sleep(1.5)

        # Step 2: Extract uh token from page
        uh = ""
        m = re.search(r'name="uh"\s+value="([^"]+)"', r.text)
        if m:
            uh = m.group(1)

        # Step 3: POST login
        log(f"Logging in as u/{username}...")
        r = s.post(
            "https://old.reddit.com/api/login",
            data={
                "user": username,
                "passwd": password,
                "api_type": "json",
                "rem": "False",
                "uh": uh,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=20
        )

        if r.status_code != 200:
            log(f"❌ Login HTTP {r.status_code}")
            return None, None

        result = r.json()
        errors = result.get("json", {}).get("errors", [])
        if errors:
            log(f"❌ Login errors: {errors}")
            return None, None

        modhash = result.get("json", {}).get("data", {}).get("modhash", "")
        if not modhash:
            # Try to get modhash from /api/me.json
            me = s.get("https://old.reddit.com/api/me.json", timeout=15)
            if me.status_code == 200:
                me_data = me.json()
                modhash = me_data.get("data", {}).get("modhash", "")

        if modhash:
            s.headers.update({"X-Modhash": modhash})
            log(f"✅ Logged in! modhash: {modhash[:8]}...")
            return s, modhash
        else:
            # Check if we're actually logged in via cookies
            me = s.get("https://old.reddit.com/api/me.json", timeout=15)
            if me.status_code == 200:
                me_data = me.json()
                name = me_data.get("data", {}).get("name", "")
                if name.lower() == username.lower():
                    modhash = me_data.get("data", {}).get("modhash", "")
                    s.headers.update({"X-Modhash": modhash})
                    log(f"✅ Logged in as u/{name}!")
                    return s, modhash

            log(f"⚠️ Could not get modhash. Response: {json.dumps(result)[:200]}")
            return None, None

    except Exception as e:
        log(f"❌ Login error: {e}")
        return None, None

# ── Reddit API Calls ─────────────────────────────────────────────────────────
def get_hot_posts(session, subreddit, limit=20):
    try:
        r = session.get(
            f"https://old.reddit.com/r/{subreddit}/hot.json?limit={limit}",
            timeout=15
        )
        if r.status_code == 200:
            posts = r.json().get("data", {}).get("children", [])
            return [p["data"] for p in posts
                    if not p["data"].get("locked")
                    and not p["data"].get("archived")]
        log(f"⚠️ r/{subreddit}: HTTP {r.status_code}")
    except Exception as e:
        log(f"⚠️ r/{subreddit}: {e}")
    return []

def post_comment(session, modhash, post_id, text):
    try:
        r = session.post(
            "https://old.reddit.com/api/comment",
            data={
                "api_type": "json",
                "thing_id": f"t3_{post_id}",
                "text": text,
                "uh": modhash,
            },
            timeout=15
        )
        if r.status_code == 200:
            result = r.json()
            errors = result.get("json", {}).get("errors", [])
            if not errors:
                return True
            log(f"⚠️ Comment errors: {errors}")
        else:
            log(f"⚠️ Comment HTTP {r.status_code}: {r.text[:100]}")
    except Exception as e:
        log(f"⚠️ Comment error: {e}")
    return False

def upvote_post(session, modhash, post_id):
    try:
        r = session.post(
            "https://old.reddit.com/api/vote",
            data={"id": f"t3_{post_id}", "dir": "1", "uh": modhash},
            timeout=10
        )
        return r.status_code == 200
    except:
        return False

def get_karma(session):
    try:
        r = session.get("https://old.reddit.com/api/me.json", timeout=10)
        if r.status_code == 200:
            d = r.json().get("data", {})
            return d.get("link_karma", 0), d.get("comment_karma", 0)
    except:
        pass
    return 0, 0

def ai_comment(post_title, subreddit):
    """Generate comment with Gemini AI, fallback to preset."""
    if GEMINI_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_KEY)
            model = genai.GenerativeModel("gemini-1.5-flash")
            resp = model.generate_content(
                f"Write a SHORT natural Reddit comment (1-2 sentences) for this post in r/{subreddit}: \"{post_title}\"\n"
                "Rules: sound human, be relevant, no hashtags/emojis/marketing. Just the comment text."
            )
            c = resp.text.strip()
            return c[:280] if len(c) > 280 else c
        except:
            pass
    return random.choice(WARMUP_COMMENTS)

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    print()
    print("=" * 60)
    print("  Zeta Warmup - Termux Edition v2")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  User: u/{USERNAME}")
    print("=" * 60)
    print()

    if not USERNAME or not PASSWORD:
        print("❌ Set REDDIT_USERNAME and REDDIT_PASSWORD environment variables!")
        sys.exit(1)

    session, modhash = reddit_login(USERNAME, PASSWORD)
    if not session:
        print("❌ Login failed. Check your Reddit username and password.")
        sys.exit(1)

    lk, ck = get_karma(session)
    log(f"📊 Karma: {lk} link / {ck} comment")

    comments_posted = 0
    upvotes_done = 0
    subs_visited = []

    subs = SUBREDDITS.copy()
    random.shuffle(subs)

    for sub in subs:
        if comments_posted >= COMMENTS_PER_RUN and upvotes_done >= UPVOTES_PER_RUN:
            break

        log(f"\n📌 r/{sub}...")
        posts = get_hot_posts(session, sub)
        if not posts:
            continue

        subs_visited.append(sub)
        log(f"   {len(posts)} posts found")

        # Upvote
        for post in posts[:3]:
            if upvotes_done >= UPVOTES_PER_RUN:
                break
            if upvote_post(session, modhash, post["id"]):
                upvotes_done += 1
                log(f"   👍 Upvoted: {post['title'][:55]}...")
                time.sleep(random.uniform(1, 3))

        # Comment
        if comments_posted < COMMENTS_PER_RUN:
            eligible = [p for p in posts if p.get("num_comments", 0) > 3]
            if eligible:
                post = random.choice(eligible[:8])
                comment = ai_comment(post["title"], sub)
                log(f"   💬 Commenting: {post['title'][:55]}...")
                log(f"   📝 \"{comment}\"")
                if post_comment(session, modhash, post["id"], comment):
                    comments_posted += 1
                    log(f"   ✅ Comment posted! ({comments_posted}/{COMMENTS_PER_RUN})")
                else:
                    log(f"   ❌ Comment failed")
                time.sleep(random.uniform(5, 10))

        time.sleep(random.uniform(3, 7))

    lk2, ck2 = get_karma(session)
    print()
    print("=" * 60)
    print("  ✅ Warmup Complete!")
    print(f"  Subreddits: {len(subs_visited)}")
    print(f"  Comments:   {comments_posted}/{COMMENTS_PER_RUN}")
    print(f"  Upvotes:    {upvotes_done}/{UPVOTES_PER_RUN}")
    print(f"  Karma now:  {lk2} link / {ck2} comment")
    print("=" * 60)
    print()

if __name__ == "__main__":
    main()
