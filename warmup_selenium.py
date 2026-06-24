#!/usr/bin/env python3
"""
Zeta Warmup - Selenium Edition (Termux)
Uses Firefox headless + geckodriver to login to Reddit and post comments.
Runs on native IP (no proxy needed). Works on Termux/Android.
"""
import os, sys, json, time, random
from datetime import datetime

USERNAME   = os.environ.get("REDDIT_USERNAME", "")
PASSWORD   = os.environ.get("REDDIT_PASSWORD", "")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

SUBREDDITS = [
    "AskReddit", "funny", "todayilearned",
    "mildlyinteresting", "worldnews", "science",
    "LifeProTips", "Showerthoughts", "technology", "pics"
]
COMMENTS_PER_RUN = 3
UPVOTES_PER_RUN  = 8

FALLBACK_COMMENTS = [
    "Great point! I've been thinking about this too.",
    "This is really interesting, thanks for sharing!",
    "I can relate to this. Well said!",
    "Thanks for the insight, very helpful!",
    "That's a fair take. Appreciate the perspective.",
    "Interesting! Never thought about it that way.",
    "Good observation. Thanks for bringing this up!",
    "Solid point, couldn't agree more.",
    "Really appreciate you sharing this.",
    "This is exactly what I needed to read today.",
]

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def ai_comment(post_title, subreddit):
    if GEMINI_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_KEY)
            model = genai.GenerativeModel("gemini-1.5-flash")
            resp = model.generate_content(
                f"Write a SHORT natural Reddit comment (1-2 sentences) for this post in r/{subreddit}:\n"
                f"\"{post_title}\"\n\n"
                "Rules: sound like a real human, be relevant, no hashtags/emojis/marketing. Just the comment text."
            )
            c = resp.text.strip()
            return c[:280] if len(c) > 280 else c
        except Exception as e:
            log(f"⚠️ Gemini error: {e}")
    return random.choice(FALLBACK_COMMENTS)

def setup_driver():
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.firefox.service import Service

    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.set_preference("general.useragent.override",
        "Mozilla/5.0 (Android 13; Mobile; rv:120.0) Gecko/120.0 Firefox/120.0")
    opts.set_preference("dom.webdriver.enabled", False)
    opts.set_preference("useAutomationExtension", False)

    service = Service(log_path="/dev/null")
    driver = webdriver.Firefox(options=opts, service=service)
    driver.set_page_load_timeout(30)
    return driver

def login(driver):
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    log("Opening Reddit login page...")
    driver.get("https://www.reddit.com/login/")
    time.sleep(3)

    wait = WebDriverWait(driver, 15)

    try:
        # Fill username
        user_field = wait.until(EC.presence_of_element_located((By.ID, "login-username")))
        user_field.clear()
        user_field.send_keys(USERNAME)
        time.sleep(0.5)

        # Fill password
        pass_field = driver.find_element(By.ID, "login-password")
        pass_field.clear()
        pass_field.send_keys(PASSWORD)
        time.sleep(0.5)

        # Click login button
        login_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_btn.click()
        log("Login button clicked, waiting...")
        time.sleep(5)

        # Check if logged in
        current_url = driver.current_url
        log(f"URL after login: {current_url}")

        if "login" not in current_url.lower():
            log(f"✅ Login successful!")
            return True
        else:
            # Try checking page source for username
            page = driver.page_source
            if USERNAME.lower() in page.lower():
                log(f"✅ Login successful (found username in page)!")
                return True
            log("❌ Still on login page")
            return False

    except Exception as e:
        log(f"❌ Login error: {e}")
        return False

def get_posts_via_api(driver, subreddit, limit=20):
    """Use Reddit JSON API with session cookies from Selenium"""
    import requests

    # Extract cookies from Selenium
    cookies = {c['name']: c['value'] for c in driver.get_cookies()}

    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Android 13; Mobile; rv:120.0) Gecko/120.0 Firefox/120.0",
    })
    for name, value in cookies.items():
        s.cookies.set(name, value, domain=".reddit.com")

    try:
        r = s.get(f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}", timeout=15)
        if r.status_code == 200:
            posts = r.json().get("data", {}).get("children", [])
            return [p["data"] for p in posts
                    if not p["data"].get("locked")
                    and not p["data"].get("archived")]
    except Exception as e:
        log(f"⚠️ API error: {e}")
    return []

def post_comment_via_browser(driver, post_url, comment_text):
    """Navigate to post and submit comment via browser"""
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    try:
        driver.get(post_url)
        time.sleep(3)

        wait = WebDriverWait(driver, 15)

        # Find comment box
        try:
            comment_box = wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "[data-testid='comment-submission-form-richtext'] div[contenteditable='true']")
            ))
        except:
            try:
                comment_box = driver.find_element(By.CSS_SELECTOR, "div[contenteditable='true']")
            except:
                log("⚠️ Comment box not found")
                return False

        comment_box.click()
        time.sleep(0.5)
        comment_box.send_keys(comment_text)
        time.sleep(1)

        # Find and click submit button
        try:
            submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_btn.click()
            time.sleep(3)
            log(f"✅ Comment submitted!")
            return True
        except Exception as e:
            log(f"⚠️ Submit button error: {e}")
            return False

    except Exception as e:
        log(f"⚠️ Browser comment error: {e}")
        return False

def upvote_via_api(driver, post_id):
    """Upvote using session cookies"""
    import requests

    cookies = {c['name']: c['value'] for c in driver.get_cookies()}
    modhash = cookies.get("modhash", "")

    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Android 13; Mobile; rv:120.0) Gecko/120.0 Firefox/120.0",
        "X-Modhash": modhash,
    })
    for name, value in cookies.items():
        s.cookies.set(name, value, domain=".reddit.com")

    try:
        r = s.post("https://www.reddit.com/api/vote",
            data={"id": f"t3_{post_id}", "dir": "1"},
            timeout=10)
        return r.status_code == 200
    except:
        return False

def main():
    print()
    print("=" * 60)
    print("  Zeta Warmup - Selenium Edition")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  User: u/{USERNAME}")
    print("=" * 60)
    print()

    if not USERNAME or not PASSWORD:
        print("❌ Set REDDIT_USERNAME and REDDIT_PASSWORD!")
        sys.exit(1)

    log("Starting Firefox (headless)...")
    try:
        driver = setup_driver()
    except Exception as e:
        log(f"❌ Firefox failed to start: {e}")
        sys.exit(1)

    try:
        if not login(driver):
            log("❌ Login failed.")
            driver.quit()
            sys.exit(1)

        comments_posted = 0
        upvotes_done = 0
        subs_visited = []

        subs = SUBREDDITS.copy()
        random.shuffle(subs)

        for sub in subs:
            if comments_posted >= COMMENTS_PER_RUN and upvotes_done >= UPVOTES_PER_RUN:
                break

            log(f"\n📌 r/{sub}...")
            posts = get_posts_via_api(driver, sub)
            if not posts:
                continue

            subs_visited.append(sub)
            log(f"   {len(posts)} posts found")

            # Upvote
            for post in posts[:3]:
                if upvotes_done >= UPVOTES_PER_RUN:
                    break
                if upvote_via_api(driver, post["id"]):
                    upvotes_done += 1
                    log(f"   👍 Upvoted: {post['title'][:55]}...")
                time.sleep(random.uniform(1, 3))

            # Comment
            if comments_posted < COMMENTS_PER_RUN:
                eligible = [p for p in posts if p.get("num_comments", 0) > 3]
                if eligible:
                    post = random.choice(eligible[:8])
                    comment = ai_comment(post["title"], sub)
                    post_url = f"https://www.reddit.com{post['permalink']}"
                    log(f"   💬 Commenting on: {post['title'][:55]}...")
                    log(f"   📝 \"{comment}\"")
                    if post_comment_via_browser(driver, post_url, comment):
                        comments_posted += 1
                        log(f"   ✅ Comment posted! ({comments_posted}/{COMMENTS_PER_RUN})")
                    else:
                        log(f"   ❌ Comment failed")
                    time.sleep(random.uniform(5, 10))

            time.sleep(random.uniform(3, 7))

        print()
        print("=" * 60)
        print("  ✅ Warmup Complete!")
        print(f"  Subreddits visited: {len(subs_visited)}")
        print(f"  Comments posted:    {comments_posted}/{COMMENTS_PER_RUN}")
        print(f"  Upvotes given:      {upvotes_done}/{UPVOTES_PER_RUN}")
        print("=" * 60)
        print()

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
