"""DataWars2 API collector for historical price data.

Fetches daily aggregated price history from api.datawars2.ie and stores
in the price_history table. Used for backfilling historical data and
on-demand fetches for items the LLM signals.

API docs: https://gitlab.com/Silvers_Gw2/Market_Data_Processer/-/wikis/endpoints#history
"""

import asyncio
import logging
import sqlite3
from datetime import datetime, timezone

import httpx

from gw2trading.db.database import get_connection

logger = logging.getLogger("gw2trading.collectors.datawars2")

BASE_URL = "https://api.datawars2.ie/gw2/v1"
REQUEST_DELAY = 1.5  # seconds between requests (be polite)
MAX_RETRIES = 3
BASE_BACKOFF = 2.0
MAX_BACKOFF = 30.0


class DataWars2Collector:
    """Fetches historical price data from the DataWars2 (Silver's GW2) API."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={"User-Agent": "gw2trading:v0.1.0 (personal project)"},
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def backfill_history(
        self,
        item_ids: list[int],
        start: str | None = None,
        end: str | None = None,
    ) -> int:
        """Fetch and store daily price history for the given items.

        Args:
            item_ids: List of GW2 item IDs to fetch history for.
            start: Start date (ISO format, e.g. "2024-01-01"). None = all available.
            end: End date (ISO format). None = up to today.

        Returns the total number of rows stored.
        """
        logger.info(f"Backfilling history for {len(item_ids)} items")
        total_stored = 0

        for i, item_id in enumerate(item_ids):
            history = await self._fetch_history(item_id, start, end)
            if history:
                stored = self._store_history(item_id, history)
                total_stored += stored
                logger.debug(f"[{i+1}/{len(item_ids)}] Item {item_id}: stored {stored} days")
            else:
                logger.debug(f"[{i+1}/{len(item_ids)}] Item {item_id}: no data returned")

            if i < len(item_ids) - 1:
                await asyncio.sleep(REQUEST_DELAY)

        logger.info(f"Backfill complete: stored {total_stored} total history rows")
        return total_stored

    async def fetch_item_history(
        self,
        item_id: int,
        start: str | None = None,
        end: str | None = None,
    ) -> int:
        """Fetch history for a single item (on-demand, e.g. when LLM signals an untracked item).

        Returns the number of rows stored.
        """
        history = await self._fetch_history(item_id, start, end)
        if history:
            return self._store_history(item_id, history)
        return 0

    async def fetch_full_catalog(self) -> int:
        """Fetch current price data for ALL items from DataWars2 /items/json.

        Stores item metadata (id, name) in the items table.
        Returns the number of items stored.
        """
        logger.info("Fetching full item catalog from DataWars2...")
        url = f"{BASE_URL}/items/json"
        data = await self._request_with_backoff(url)
        if not data:
            logger.error("Failed to fetch item catalog")
            return 0

        conn = get_connection()
        stored = 0
        try:
            for item in data:
                item_id = item.get("id")
                name = item.get("name", "Unknown")
                if item_id and name:
                    conn.execute(
                        """INSERT OR IGNORE INTO items (item_id, name)
                           VALUES (?, ?)""",
                        (item_id, name),
                    )
                    stored += 1
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Database error storing catalog: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()

        logger.info(f"Catalog: stored {stored} items")
        return stored

    async def _fetch_history(
        self, item_id: int, start: str | None, end: str | None
    ) -> list[dict] | None:
        """Fetch daily history for a single item."""
        params = {"itemID": item_id}
        if start:
            params["start"] = start
        if end:
            params["end"] = end

        url = f"{BASE_URL}/history"
        client = await self._get_client()
        backoff = BASE_BACKOFF

        for attempt in range(MAX_RETRIES):
            try:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    logger.warning(f"Rate limited, backing off {backoff}s")
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, MAX_BACKOFF)
                elif response.status_code == 404:
                    return None
                else:
                    logger.warning(
                        f"HTTP {response.status_code} for item {item_id} (attempt {attempt+1})"
                    )
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, MAX_BACKOFF)
            except httpx.RequestError as e:
                logger.error(f"Request error for item {item_id}: {e}")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, MAX_BACKOFF)

        logger.error(f"Failed after {MAX_RETRIES} attempts for item {item_id}")
        return None

    async def _request_with_backoff(self, url: str) -> list[dict] | None:
        """Generic GET with backoff for non-history endpoints."""
        client = await self._get_client()
        backoff = BASE_BACKOFF

        for attempt in range(MAX_RETRIES):
            try:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, MAX_BACKOFF)
                else:
                    logger.error(f"HTTP {response.status_code} for {url[:80]}")
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, MAX_BACKOFF)
            except httpx.RequestError as e:
                logger.error(f"Request error: {e}")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, MAX_BACKOFF)

        return None

    def _store_history(self, item_id: int, history: list[dict]) -> int:
        """Store daily history rows into price_history table."""
        conn = get_connection()
        rows = []

        for record in history:
            date_str = record.get("date", "")
            if date_str:
                # Normalize to YYYY-MM-DD
                date_str = date_str[:10]

            rows.append((
                item_id,
                date_str,
                record.get("buy_price_avg"),
                record.get("buy_price_min"),
                record.get("buy_price_max"),
                record.get("buy_price_stdev"),
                record.get("sell_price_avg"),
                record.get("sell_price_min"),
                record.get("sell_price_max"),
                record.get("sell_price_stdev"),
                record.get("buy_quantity_avg"),
                record.get("sell_quantity_avg"),
                record.get("buy_sold"),
                record.get("sell_sold"),
                record.get("buy_listed"),
                record.get("sell_listed"),
                record.get("buy_delisted"),
                record.get("sell_delisted"),
                record.get("buy_value"),
                record.get("sell_value"),
                record.get("count"),
            ))

        try:
            conn.executemany(
                """INSERT OR IGNORE INTO price_history
                   (item_id, date, buy_price_avg, buy_price_min, buy_price_max,
                    buy_price_stdev, sell_price_avg, sell_price_min, sell_price_max,
                    sell_price_stdev, buy_quantity_avg, sell_quantity_avg,
                    buy_sold, sell_sold, buy_listed, sell_listed,
                    buy_delisted, sell_delisted, buy_value, sell_value, snapshot_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                rows,
            )
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Database error storing history for item {item_id}: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()

        return len(rows)

    def update_last_accessed(self, item_ids: list[int]) -> None:
        """Update last_accessed timestamp for items (called when LLM uses the data)."""
        conn = get_connection()
        now = datetime.now(timezone.utc).isoformat()
        try:
            placeholders = ",".join("?" for _ in item_ids)
            conn.execute(
                f"""UPDATE price_history SET last_accessed = ?
                    WHERE item_id IN ({placeholders})""",
                [now] + item_ids,
            )
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error updating last_accessed: {e}")
        finally:
            conn.close()

    def cleanup_stale_history(self, retention_days: int = 90) -> int:
        """Delete history for non-tracked items not accessed in retention_days.

        Tracked items (in TOP_200) are never cleaned up.
        Returns number of rows deleted.
        """
        from gw2trading.collectors.tracked_items import TOP_200_ITEM_IDS

        conn = get_connection()
        tracked_placeholders = ",".join("?" for _ in TOP_200_ITEM_IDS)

        try:
            cursor = conn.execute(
                f"""DELETE FROM price_history
                    WHERE item_id NOT IN ({tracked_placeholders})
                    AND last_accessed < datetime('now', ?)""",
                TOP_200_ITEM_IDS + [f"-{retention_days} days"],
            )
            deleted = cursor.rowcount
            conn.commit()
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} stale history rows")
            return deleted
        except sqlite3.Error as e:
            logger.error(f"Error during cleanup: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()
