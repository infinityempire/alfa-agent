# Reddit Distributor Agent

A Multi-Agent marketing and distribution system for Reddit, designed to run in a Linux/Termux environment.

## Overview

This system consists of three distinct components that work together in a pipeline:

1. **Reddit Scraper & Matcher Agent**: Periodically fetches recent posts from target subreddits using the Reddit API (PRAW)
2. **Contextual Writer Agent (Vibe-Checker)**: Processes matched posts alongside local Delta reporting data and uses Google Gemini API to generate tailored, human-sounding Reddit comments
3. **Humanization & Publishing Engine**: Manages publishing schedules, implements random delays (7-25 minutes), and posts comments to Reddit without triggering bot-detection

## Project Structure

```
reddit_distributor_agent/
├── agents/
│   ├── __init__.py
│   ├── reddit_scraper.py      # PRAW-based subreddit scraper
│   ├── gemini_writer.py       # Gemini API comment generator
│   └── publishing_engine.py   # Humanized comment publisher
├── config/
│   ├── __init__.py
│   └── settings.py            # All configuration settings
├── utils/
│   ├── __init__.py
│   ├── logger.py              # Colored logging utilities
│   ├── state.py               # State persistence manager
│   └── delay.py               # Random delay utilities
├── data/
│   ├── delta_reporting_data.json  # Your business metrics
│   ├── processed_posts.json       # Track processed posts
│   ├── state.json                  # Agent state
│   └── generated_comments.json     # Saved comments
├── logs/
│   └── reddit_agent.log       # Application logs
├── main.py                    # Central controller
├── requirements.txt           # Python dependencies
├── .env.example              # Environment template
└── README.md
```

## Setup

### 1. Install Dependencies

```bash
cd reddit_distributor_agent
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Reddit API Credentials
# Create a Reddit app at: https://www.reddit.com/prefs/apps
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=your_app_name_v1.0 (by u/your_username)
REDDIT_USERNAME=your_reddit_username
REDDIT_PASSWORD=your_reddit_password

# Google Gemini API Key
# Get your API key at: https://makersuite.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key

# Application Settings
DRY_RUN=true
LOG_LEVEL=INFO
```

### 3. Configure Your Data

Edit `data/delta_reporting_data.json` with your company's metrics:

```json
{
  "company_metrics": {
    "mrr": "$12,500",
    "arr": "$150,000",
    "customers": 89,
    "churn_rate": "2.1%",
    "nps_score": 72
  },
  "recent_milestones": [...],
  "lessons_learned": [...],
  "growth_strategies": [...]
}
```

### 4. Configure Target Subreddits

Edit `config/settings.py` to customize target subreddits:

```python
TARGET_SUBREDDITS = [
    "startups",
    "entrepreneur", 
    "smallbusiness",
    "SideProject",
    "SaaS",
]
```

## Usage

### Test Connections

```bash
python main.py test
```

### Scrape Posts Only

```bash
python main.py scrape --subreddits startups entrepreneur
```

### Generate Comments Only

```bash
python main.py generate --max-posts 5
```

### Run Full Pipeline (Dry Run)

```bash
python main.py run --dry-run --max-posts 3
```

### Run Full Pipeline (Live)

```bash
python main.py run --live --max-posts 5
```

### Print Previously Generated Comments

```bash
python main.py --print-comments
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `--mode` | Execution mode: `run`, `scrape`, `generate`, `test` |
| `--dry-run` | Don't post to Reddit (default) |
| `--live` | Actually post to Reddit |
| `--subreddits` | Specific subreddits to target |
| `--max-posts` | Maximum posts to process |
| `--limit` | Posts per subreddit (default: 20) |
| `--print-comments` | Print saved generated comments |

## Pipeline Flow

1. **Scraping Phase**
   - Fetches posts from configured subreddits
   - Filters by score, upvote ratio, and age
   - Skips already processed posts

2. **Generation Phase**
   - Loads Delta reporting data
   - Fetches existing comments for context
   - Generates human-like comments using Gemini

3. **Publishing Phase**
   - Adds random delay (7-25 minutes) between posts
   - Simulates human typing patterns
   - Posts to Reddit (or logs in dry-run mode)

## Safety Features

- **Dry-run mode** by default - never posts accidentally
- **Random delays** between posts (7-25 minutes)
- **Processed post tracking** - never posts the same content twice
- **Human-like timing** with jitter
- **Rate limiting awareness** built into PRAW

## Customization

### Adjust Publishing Delays

Edit `config/settings.py`:

```python
PUBLISHING_CONFIG = {
    "min_delay_minutes": 7,
    "max_delay_minutes": 25,
    "max_posts_per_run": 5,
    "dry_run": True,
}
```

### Change Gemini Writing Style

Edit the system prompt in `config/settings.py`:

```python
WRITING_CONFIG = {
    "system_prompt": """Write like an experienced, supportive founder...""",
}
```

### Add More Subreddits

```python
TARGET_SUBREDDITS = [
    "startups",
    "entrepreneur",
    "smallbusiness",
    "SideProject",
    "SaaS",
    "marketing",
    "business",
]
```

## Logs

Logs are written to:
- Console (INFO level)
- `logs/reddit_agent.log` (DEBUG level)

## Scheduling

To run periodically, add to crontab:

```bash
# Run every hour at minute 0
0 * * * * cd /path/to/reddit_distributor_agent && python main.py run --dry-run >> /path/to/logs/cron.log 2>&1

# Run every 6 hours
0 */6 * * * cd /path/to/reddit_distributor_agent && python main.py run --live --max-posts 3 >> /path/to/logs/cron.log 2>&1
```

## Troubleshooting

### Reddit API Errors

- Ensure your Reddit app is configured as "script" type
- Check that username/password is correct
- Verify your Reddit account has 2FA disabled or use an app-specific password

### Gemini API Errors

- Check your API key is valid
- Ensure billing is set up on Google AI Studio
- Check rate limits

### Empty Results

- Target subreddits may have no matching posts
- Check LOG_LEVEL is set to DEBUG
- Review logs in `logs/reddit_agent.log`

## License

MIT License
