"""Reddit collector using public JSON endpoint (no auth required).

Fetches recent posts from r/Guildwars2 and stores them for sentiment analysis."""
 
import asyncio
import logging
import sqlite3
from datetime import datetime, timezone
 
import httpx
 
from gw2trading.db.database import get_connection


logger = logging.getLogger("gw2trading.collectors.reddit")
SUBREDDIT_URL = "https://www.reddit.com/r/Guildwars2/new.json"
USER_AGENT = "gw2trading:v0.1.0 (personal project)"
REQUEST_DELAY = 2.0


class RedditCollector:
    """Fetches recent posts from r/Guildwars2 using public JSON API."""
 
    def __init__(self) -> None:
         self._client: httpx.AsyncClient | None = None
 
    async def _get_client(self) -> httpx.AsyncClient:
         if self._client is None or self._client.is_closed:
             self._client = httpx.AsyncClient(
                 timeout=30.0,
                 headers={"User-Agent": USER_AGENT},
             )
         return self._client
 
    async def close(self) -> None:
         if self._client and not self._client.is_closed:
             await self._client.aclose()
 
    async def collect_posts(self, limit: int = 25) -> int:
        """Fetch recent posts and store in DB. Returns count stored."""
        params = {"limit": limit}
        client = await self._get_client()
        try:
            response = await client.get(SUBREDDIT_URL, params=params)
            response.raise_for_status()
            data = response.json()
            posts = []
            for child in data.get("data", {}).get("children", []):
                post_data = child.get("data", {})
                created_utc = post_data.get("created_utc")
                if created_utc is not None:
                    timestamp = datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat()
                else:
                    timestamp = None
                permalink = "https://www.reddit.com" + post_data.get("permalink", "")
                posts.append({
                    "post_id": post_data.get("id"),
                    "title": post_data.get("title"),
                    "body": post_data.get("selftext"),
                    "upvotes": post_data.get("ups"),
                    "comment_count": post_data.get("num_comments"),
                    "timestamp": timestamp,
                    "url": permalink,
                })
            stored_count = self._store_posts(posts)
            return stored_count
        except httpx.HTTPError as e:
            logger.error(f"HTTP error while fetching Reddit posts: {e}")
            return 0
        except Exception as e:
            logger.error(f"Unexpected error while collecting Reddit posts: {e}")
            return 0         


 
    def _store_posts(self, posts: list[dict]) -> int:
        """Insert posts into reddit_posts table. Returns count stored."""
    
        conn = get_connection()
        rows = []
        for post in posts:
            rows.append((
                post.get("post_id", ""),
                post.get("title", ""),
                post.get("body", ""),
                post.get("upvotes", 0),
                post.get("comment_count", 0),
                post.get("timestamp", ""),
                post.get("url", "")
            ))
        try:
            conn.executemany(
                """INSERT OR IGNORE INTO reddit_posts
                   (post_id, title, body, upvotes, comment_count, timestamp, url)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                rows,
            )
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Database error storing Reddit posts: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()
        
        return len(rows)
    
        