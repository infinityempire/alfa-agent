"""
Reddit Scraper & Matcher Agent.
Fetches recent posts from target subreddits using PRAW.
"""
import praw
from praw.models import Submission
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from config.settings import REDDIT_CONFIG, SCRAPING_CONFIG, TARGET_SUBREDDITS
from utils.logger import logger
from utils.state import state_manager


class RedditScraperAgent:
    """
    Agent responsible for scraping posts from Reddit subreddits.
    """
    
    def __init__(self):
        """Initialize the Reddit scraper agent."""
        self.reddit = None
        self._initialize_reddit()
    
    def _initialize_reddit(self) -> None:
        """Initialize the Reddit API connection."""
        try:
            self.reddit = praw.Reddit(
                client_id=REDDIT_CONFIG["client_id"],
                client_secret=REDDIT_CONFIG["client_secret"],
                user_agent=REDDIT_CONFIG["user_agent"],
                username=REDDIT_CONFIG["username"],
                password=REDDIT_CONFIG["password"],
            )
            # Test connection
            self.reddit.user.me()
            logger.info("Successfully connected to Reddit API")
        except Exception as e:
            logger.error(f"Failed to initialize Reddit connection: {e}")
            raise
    
    def _is_post_relevant(self, submission: Submission) -> bool:
        """
        Check if a post is relevant based on configurable criteria.
        
        Args:
            submission: Reddit submission object
            
        Returns:
            True if post meets relevance criteria
        """
        # Check minimum score
        if submission.score < SCRAPING_CONFIG["min_score"]:
            return False
        
        # Check upvote ratio
        if hasattr(submission, "upvote_ratio") and submission.upvote_ratio < SCRAPING_CONFIG["min_upvote_ratio"]:
            return False
        
        # Check post age
        post_age = datetime.now().timestamp() - submission.created_utc
        max_age_seconds = SCRAPING_CONFIG["max_age_hours"] * 3600
        if post_age > max_age_seconds:
            return False
        
        return True
    
    def _submission_to_dict(self, submission: Submission) -> Dict[str, Any]:
        """
        Convert a submission to a dictionary for easier processing.
        
        Args:
            submission: Reddit submission object
            
        Returns:
            Dictionary with submission data
        """
        return {
            "id": submission.id,
            "title": submission.title,
            "selftext": submission.selftext,
            "url": submission.url,
            "subreddit": str(submission.subreddit),
            "score": submission.score,
            "upvote_ratio": getattr(submission, "upvote_ratio", None),
            "num_comments": submission.num_comments,
            "created_utc": submission.created_utc,
            "created_datetime": datetime.fromtimestamp(submission.created_utc).isoformat(),
            "author": str(submission.author) if submission.author else "[deleted]",
            "permalink": f"https://reddit.com{submission.permalink}",
            "flair": getattr(submission, "link_flair_text", None),
        }
    
    async def fetch_posts(
        self,
        subreddits: Optional[List[str]] = None,
        limit: Optional[int] = None,
        sort_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch posts from target subreddits.
        
        Args:
            subreddits: List of subreddit names (defaults to TARGET_SUBREDDITS)
            limit: Maximum posts per subreddit
            sort_type: Sort method (hot, new, top, rising)
            
        Returns:
            List of post dictionaries
        """
        if subreddits is None:
            subreddits = TARGET_SUBREDDITS
        
        if limit is None:
            limit = SCRAPING_CONFIG["max_posts_per_subreddit"]
        
        if sort_type is None:
            sort_type = SCRAPING_CONFIG["sort_type"]
        
        all_posts = []
        
        for subreddit_name in subreddits:
            try:
                logger.info(f"Fetching posts from r/{subreddit_name} (sort: {sort_type})")
                
                subreddit = self.reddit.subreddit(subreddit_name)
                
                # Get posts based on sort type
                if sort_type == "hot":
                    posts = subreddit.hot(limit=limit)
                elif sort_type == "new":
                    posts = subreddit.new(limit=limit)
                elif sort_type == "top":
                    posts = subreddit.top(limit=limit)
                elif sort_type == "rising":
                    posts = subreddit.rising(limit=limit)
                else:
                    posts = subreddit.hot(limit=limit)
                
                for post in posts:
                    # Check if already processed
                    if state_manager.is_post_processed(post.id):
                        logger.debug(f"Skipping already processed post: {post.id}")
                        continue
                    
                    # Check relevance
                    if not self._is_post_relevant(post):
                        continue
                    
                    post_dict = self._submission_to_dict(post)
                    all_posts.append(post_dict)
                    logger.debug(f"Found relevant post: {post.title[:50]}...")
                
                # Update subreddit timestamp
                state_manager.update_subreddit_timestamp(subreddit_name)
                logger.info(f"Fetched {len([p for p in all_posts if p['subreddit'] == subreddit_name])} relevant posts from r/{subreddit_name}")
                
            except praw.exceptions.PRAWException as e:
                logger.error(f"PRAW error fetching from r/{subreddit_name}: {e}")
            except Exception as e:
                logger.error(f"Error fetching from r/{subreddit_name}: {e}")
        
        logger.info(f"Total relevant posts fetched: {len(all_posts)}")
        return all_posts
    
    def get_post_details(self, post_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific post.
        
        Args:
            post_id: Reddit post ID
            
        Returns:
            Post dictionary or None if not found
        """
        try:
            submission = self.reddit.submission(id=post_id)
            return self._submission_to_dict(submission)
        except Exception as e:
            logger.error(f"Error fetching post {post_id}: {e}")
            return None
    
    def get_post_comments(self, post_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get comments from a specific post.
        
        Args:
            post_id: Reddit post ID
            limit: Maximum number of comments
            
        Returns:
            List of comment dictionaries
        """
        try:
            submission = self.reddit.submission(id=post_id)
            submission.comments.replace_more(limit=3)  # Limit expansion of MoreComments
            
            comments = []
            for comment in submission.comments[:limit]:
                if hasattr(comment, "body") and comment.body != "[deleted]":
                    comments.append({
                        "id": comment.id,
                        "body": comment.body,
                        "author": str(comment.author) if comment.author else "[deleted]",
                        "score": comment.score,
                        "created_utc": comment.created_utc,
                        "is_submitter": comment.is_submitter,
                    })
            
            return comments
        except Exception as e:
            logger.error(f"Error fetching comments for post {post_id}: {e}")
            return []
    
    async def get_subreddit_info(self, subreddit_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a subreddit.
        
        Args:
            subreddit_name: Name of the subreddit
            
        Returns:
            Subreddit info dictionary or None
        """
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            return {
                "name": subreddit.display_name,
                "title": subreddit.title,
                "description": subreddit.description,
                "subscribers": getattr(subreddit, "subscribers", 0),
                "active_users": getattr(subreddit, "active_user_count", 0),
                "public_description": subreddit.public_description,
            }
        except Exception as e:
            logger.error(f"Error fetching subreddit info for r/{subreddit_name}: {e}")
            return None
    
    def test_connection(self) -> bool:
        """
        Test the Reddit API connection.
        
        Returns:
            True if connection is successful
        """
        try:
            user = self.reddit.user.me()
            logger.info(f"Reddit connection test successful. Logged in as: {user}")
            return True
        except Exception as e:
            logger.error(f"Reddit connection test failed: {e}")
            return False
