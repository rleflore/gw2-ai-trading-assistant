"""GW2 Wiki patch notes collector.

Fetches game update pages from wiki.guildwars2.com via the MediaWiki API
and stores them in the patch_notes table.
"""

import asyncio
import logging
import re
import sqlite3
from datetime import datetime

import httpx

from gw2trading.config import settings
from gw2trading.db.database import get_connection

logger = logging.getLogger("gw2trading.collectors.wiki")

WIKI_API_URL = "https://wiki.guildwars2.com/api.php"
REQUEST_DELAY = 1.0  # seconds between page fetches (be polite)
MAX_RETRIES = 5
BASE_BACKOFF = 1.0
MAX_BACKOFF = 60.0


class WikiCollector:
    """Async collector for GW2 Wiki patch notes."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def collect_patch_notes(self, since: str | None = None) -> int:
        """Fetch and store patch notes newer than `since` (YYYY-MM-DD).

        If since is None, checks the DB for the latest date and fetches from there.
        Returns the number of notes stored.
        """
        logger.info(f"Collecting patch notes since {since or 'latest in DB'}")
        total_stored = 0

        if since is None:
            since = self._get_latest_date_from_db()
            if since:
                logger.info(f"Latest patch note in DB is from {since}")
        
        pages = await self._get_update_pages(since)
        for page in pages:
            title = page.get("title", "")
            date = page.get("date", "")
            if not title or not date:
                continue
            content = await self._fetch_page_content(title)
            if content:
                note = {
                    "date": date,
                    "title": title,
                    "full_text": content,
                    "source_url": f"https://wiki.guildwars2.com/wiki/{title.replace(' ', '_')}"
                }
                stored = self._store_patch_notes([note])
                total_stored += stored
                await asyncio.sleep(REQUEST_DELAY)
        
        logger.info(f"Stored {total_stored} patch notes")
        return total_stored

            
        

    async def _get_update_pages(self, since: str | None = None) -> list[dict]:
        """Fetch list of game update pages from the wiki.
        If `since` is provided, only return pages with dates newer than `since`."""

        params = {
            "action" : "query",
            "list" : "allpages",
            "apprefix" : "Game updates/",
            "aplimit" : 500,
            "format" : "json"
        }

        client = await self._get_client()
        pages = []
        apcontinue = None
        
        since_date = datetime.strptime(since, "%Y-%m-%d") if since else None
        while True:
            if apcontinue:
                params["apcontinue"] = apcontinue
            response = await client.get(WIKI_API_URL, params=params)
            if response.status_code != 200:
                logger.error(f"Failed to fetch category members: {response.status_code}")
                break
            data = response.json()
            parses = data.get("query", {}).get("allpages", [])
            for page in parses:
                title = page.get("title", "")
                match = re.match(r"Game updates/(\d{4}-\d{2}-\d{2})", title)
                if match:
                    date_str = match.group(1)
                    page_date = datetime.strptime(date_str, "%Y-%m-%d")
                    if since_date is None or page_date > since_date:
                        pages.append({"title": title, "date": date_str})
            apcontinue = data.get("continue", {}).get("apcontinue")
            if not apcontinue:
                break
        
        return pages



    async def _fetch_page_content(self, title: str) -> str:
        """Fetch parsed content for a single wiki page.

        Returns cleaned plaintext.
        """
        
        params = {
            "action" : "parse",
            "page" : title,
            "prop" : "wikitext",
            "format" : "json"
        }

        client = await self._get_client()
        response = await client.get(WIKI_API_URL, params=params)
        if response.status_code != 200:
            logger.error(f"Failed to fetch page content for {title}: {response.status_code}")
            return ""
        data = response.json()
        raw_wikitext = data.get("parse", {}).get("wikitext", {}).get("*", "")
        if not raw_wikitext:
            logger.warning(f"No wikitext found for {title}")
            return ""
        return self._strip_wikitext(raw_wikitext)

    def _strip_wikitext(self, raw: str) -> str:
        text = raw
        patterns = [
            (r"\{\{[^}]+\}\}", ""), #  {{...}} templates
            (r"\[\[[^|\]]+\|([^]]+)\]\]", r"\1"), # [[...]] links (keep display text)
            (r"\[\[([^]]+)\]\]", r"\1"),  # [[Page]] -> Page
            (r"=+\s*(.+?)\s*=+", r"\1"),  # == Heading == -> Heading
            (r"''+", ""),  # ''italics'' and '''bold''' -> remove
            (r"\n{3,}", "\n\n"),  # collapse multiple newlines
        ]
        for pattern, repl in patterns:
            text = re.sub(pattern, repl, text)
        return text.strip()

        

    def _get_latest_date_from_db(self) -> str | None:
        conn = get_connection()
        result = conn.execute("SELECT MAX(date) FROM patch_notes").fetchone()
        latest_date = result[0] if result and result[0] else None
        conn.close()
        return latest_date

    def _store_patch_notes(self, notes: list[dict]) -> int:
        """Insert patch notes into the database.

        Each note dict should have: date, title, full_text, source_url
        Returns number of rows inserted.
        """
        conn = get_connection()
        rows = []

        for note in notes:
            rows.append((
                note.get("date", ""),
                note.get("title", ""),
                note.get("full_text", ""),
                note.get("source_url", "")
            ))
    
        try:
            conn.executemany(
                """INSERT OR IGNORE INTO patch_notes
                   (date, title, full_text, source_url)
                   VALUES (?, ?, ?, ?)""",
                rows,
            )
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Database error storing patch notes: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()
        return len(rows)