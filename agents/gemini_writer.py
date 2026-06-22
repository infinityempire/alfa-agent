"""
Contextual Writer Agent (Vibe-Checker).
Uses Google Gemini API to generate tailored, human-sounding Reddit comments.
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from google import genai
from google.genai import types

from config.settings import GEMINI_CONFIG, WRITING_CONFIG, DELTA_DATA_PATH
from utils.logger import logger


class GeminiWriterAgent:
    """
    Agent responsible for generating human-like Reddit comments using Gemini.
    """
    
    def __init__(self):
        """Initialize the Gemini writer agent."""
        self.client = None
        self.model = GEMINI_CONFIG["model"]
        self._initialize_client()
        self._load_delta_data()
    
    def _initialize_client(self) -> None:
        """Initialize the Gemini API client."""
        try:
            self.client = genai.Client(api_key=GEMINI_CONFIG["api_key"])
            logger.info(f"Gemini client initialized with model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            raise
    
    def _load_delta_data(self) -> None:
        """Load local Delta reporting data."""
        try:
            if DELTA_DATA_PATH.exists():
                with open(DELTA_DATA_PATH, "r", encoding="utf-8") as f:
                    self.delta_data = json.load(f)
                logger.info(f"Loaded Delta data from {DELTA_DATA_PATH}")
            else:
                logger.warning(f"Delta data file not found at {DELTA_DATA_PATH}. Using empty data.")
                self.delta_data = self._create_sample_delta_data()
                self._save_delta_data()
        except Exception as e:
            logger.error(f"Error loading Delta data: {e}")
            self.delta_data = self._create_sample_delta_data()
    
    def _create_sample_delta_data(self) -> Dict[str, Any]:
        """Create sample Delta data for testing."""
        return {
            "company_metrics": {
                "mrr": "$12,500",
                "arr": "$150,000",
                "customers": 89,
                "churn_rate": "2.1%",
                "nps_score": 72,
            },
            "recent_milestones": [
                "Launched new onboarding flow with 40% better activation",
                "Integrated with Slack for team notifications",
                "Reduced support tickets by 25% with better documentation",
            ],
            "lessons_learned": [
                "Start charging earlier than you think you're ready",
                "Customer interviews > surveys for understanding needs",
                "Build in public creates unexpected opportunities",
            ],
            "growth_strategies": [
                "Content marketing drives 60% of our signups",
                "Referral program accounts for 20% of new customers",
                "Partnerships with complementary tools work well",
            ],
        }
    
    def _save_delta_data(self) -> None:
        """Save Delta data to file."""
        try:
            with open(DELTA_DATA_PATH, "w", encoding="utf-8") as f:
                json.dump(self.delta_data, f, indent=2)
            logger.info(f"Saved Delta data to {DELTA_DATA_PATH}")
        except Exception as e:
            logger.error(f"Error saving Delta data: {e}")
    
    def _build_system_prompt(self) -> str:
        """
        Build the system prompt for comment generation.
        
        Returns:
            System prompt string
        """
        base_prompt = WRITING_CONFIG["system_prompt"]
        
        # Add context about Delta data
        delta_context = f"""
        
Additional context from our operational data:
- Monthly Revenue: {self.delta_data['company_metrics'].get('mrr', 'N/A')}
- Annual Revenue: {self.delta_data['company_metrics'].get('arr', 'N/A')}
- Customer Count: {self.delta_data['company_metrics'].get('customers', 'N/A')}
- Churn Rate: {self.delta_data['company_metrics'].get('churn_rate', 'N/A')}
- NPS Score: {self.delta_data['company_metrics'].get('nps_score', 'N/A')}

Recent Milestones:
{chr(10).join(f"- {m}" for m in self.delta_data['lessons_learned'][:3])}

Key Lessons:
{chr(10).join(f"- {l}" for l in self.delta_data['lessons_learned'][:3])}

What Works for Growth:
{chr(10).join(f"- {g}" for g in self.delta_data['growth_strategies'][:3])}
"""
        return base_prompt + delta_context
    
    def _build_user_prompt(self, post: Dict[str, Any], comments: List[Dict[str, Any]] = None) -> str:
        """
        Build the user prompt for comment generation.
        
        Args:
            post: Post dictionary with title and content
            comments: Optional list of existing comments for context
            
        Returns:
            User prompt string
        """
        prompt = f"""Write a Reddit comment responding to this post:

Title: {post['title']}

Content: {post.get('selftext', 'No text content') or 'Link post - check URL'}

"""
        
        if comments:
            prompt += "Existing comments for context:\n"
            for i, comment in enumerate(comments[:3], 1):
                prompt += f"\n{i}. By {comment['author']}: {comment['body'][:200]}..."
        
        prompt += f"""

Write a helpful, authentic comment that:
1. Provides genuine value based on the post's topic
2. References relevant insights from our operational data where applicable
3. Asks a thoughtful follow-up question to encourage engagement
4. Sounds like a real founder sharing experience, not a salesperson

Keep the comment under {WRITING_CONFIG['max_response_length']} characters.
Do not use these words: delve, revolutionary, landscape, critical, game-changer, cutting-edge.
"""
        return prompt
    
    async def generate_comment(
        self,
        post: Dict[str, Any],
        comments: List[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Generate a comment for a Reddit post.
        
        Args:
            post: Post dictionary
            comments: Optional list of existing comments
            
        Returns:
            Generated comment text or None on failure
        """
        try:
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(post, comments)
            
            logger.debug(f"Generating comment for post: {post['title'][:50]}...")
            
            response = self.client.models.generate_content(
                model=self.model,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=WRITING_CONFIG["temperature"],
                    max_output_tokens=1024,
                ),
                contents=user_prompt,
            )
            
            if response.text:
                comment = response.text.strip()
                logger.info(f"Generated comment ({len(comment)} chars) for post {post['id']}")
                return comment
            else:
                logger.warning(f"Empty response from Gemini for post {post['id']}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating comment: {e}")
            return None
    
    async def generate_comments_batch(
        self,
        posts: List[Dict[str, Any]],
        comments_map: Dict[str, List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate comments for multiple posts in batch.
        
        Args:
            posts: List of post dictionaries
            comments_map: Optional dict mapping post_id to comments list
            
        Returns:
            List of result dictionaries with post_id and generated comment
        """
        results = []
        
        for post in posts:
            comments = comments_map.get(post["id"]) if comments_map else None
            
            comment = await self.generate_comment(post, comments)
            
            results.append({
                "post_id": post["id"],
                "post_title": post["title"],
                "post_subreddit": post["subreddit"],
                "generated_comment": comment,
                "timestamp": datetime.now().isoformat(),
                "success": comment is not None,
            })
            
            # Small delay between API calls to avoid rate limiting
            import asyncio
            await asyncio.sleep(1)
        
        successful = sum(1 for r in results if r["success"])
        logger.info(f"Generated {successful}/{len(results)} comments successfully")
        
        return results
    
    def save_generated_comments(self, results: List[Dict[str, Any]], filepath: str = None) -> None:
        """
        Save generated comments to a JSON file.
        
        Args:
            results: List of result dictionaries
            filepath: Optional custom filepath
        """
        from config.settings import GENERATED_COMMENTS_FILE
        
        save_path = Path(filepath) if filepath else GENERATED_COMMENTS_FILE
        
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, default=str)
            logger.info(f"Saved {len(results)} generated comments to {save_path}")
        except Exception as e:
            logger.error(f"Error saving generated comments: {e}")
    
    def update_delta_data(self, new_data: Dict[str, Any]) -> None:
        """
        Update the Delta data with new information.
        
        Args:
            new_data: Dictionary with updated data
        """
        self.delta_data.update(new_data)
        self._save_delta_data()
        logger.info("Delta data updated")
