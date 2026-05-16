"""GW2 API price collector.

Fetches prices from /v2/commerce/prices in batches and stores snapshots in SQLite.
"""

import asyncio
import logging
import sqlite3
from datetime import datetime, timezone

import httpx

from gw2trading.config import settings
from gw2trading.db.database import get_connection

logger = logging.getLogger("gw2trading.collectors.price")

MAX_BATCH_SIZE = 200
MAX_RETRIES = 5
BASE_BACKOFF = 1.0  # seconds
MAX_BACKOFF = 60.0


class PriceCollector:
    """Async collector for GW2 Trading Post prices."""

    def __init__(self) -> None:
        self.base_url = settings.gw2_api_base_url
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def collect_prices(self, item_ids: list[int]) -> int:
        """Fetch prices for given item IDs and store in database.

        Returns the number of snapshots stored.
        """
        logger.info(f"Collecting prices for {len(item_ids)} items")
        total_stored = 0

        for batch in self._batch(item_ids, MAX_BATCH_SIZE):
            prices = await self._fetch_prices(batch)
            if prices:
                stored = self._store_prices(prices)
                total_stored += stored

        logger.info(f"Stored {total_stored} price snapshots")
        return total_stored

    async def fetch_and_store_item_metadata(self, item_ids: list[int]) -> int:
        """Fetch item details from /v2/items and upsert into items table.

        Returns the number of items stored.
        """
        logger.info(f"Fetching metadata for {len(item_ids)} items")
        total_stored = 0

        for batch in self._batch(item_ids, MAX_BATCH_SIZE):
            items = await self._fetch_items(batch)
            if items:
                stored = self._store_items(items)
                total_stored += stored

        logger.info(f"Stored metadata for {total_stored} items")
        return total_stored

    async def _fetch_prices(self, item_ids: list[int]) -> list[dict] | None:
        """Fetch prices from /v2/commerce/prices with retry and backoff."""
        ids_param = ",".join(str(i) for i in item_ids)
        url = f"{self.base_url}/commerce/prices?ids={ids_param}"
        return await self._request_with_backoff(url)

    async def _fetch_items(self, item_ids: list[int]) -> list[dict] | None:
        """Fetch item metadata from /v2/items with retry and backoff."""
        ids_param = ",".join(str(i) for i in item_ids)
        url = f"{self.base_url}/items?ids={ids_param}"
        return await self._request_with_backoff(url)

    async def _request_with_backoff(self, url: str) -> list[dict] | None:
        """Make a GET request with exponential backoff on failure/429."""
        client = await self._get_client()
        backoff = BASE_BACKOFF

        for attempt in range(MAX_RETRIES):
            try:
                response = await client.get(url)

                if response.status_code in (200, 206):
                    # 206 = partial content (some IDs not tradeable), still valid data
                    return response.json()
                elif response.status_code == 429:
                    logger.warning(f"Rate limited (429), backing off {backoff}s")
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, MAX_BACKOFF)
                elif response.status_code == 404:
                    logger.warning(f"Not found (404): {url[:80]}")
                    return None
                else:
                    logger.error(f"HTTP {response.status_code} for {url[:80]}")
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, MAX_BACKOFF)

            except httpx.RequestError as e:
                logger.error(f"Request error (attempt {attempt + 1}): {e}")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, MAX_BACKOFF)

        logger.error(f"Failed after {MAX_RETRIES} attempts: {url[:80]}")
        return None

    def _store_prices(self, prices: list[dict]) -> int:
        """Insert price data into price_snapshots table."""
        conn = get_connection()
        timestamp = datetime.now(timezone.utc).isoformat()
        rows = []

        for p in prices:
            buys = p.get("buys", {})
            sells = p.get("sells", {})
            rows.append((
                p["id"],
                timestamp,
                buys.get("unit_price", 0),
                sells.get("unit_price", 0),
                buys.get("quantity", 0),
                sells.get("quantity", 0),
            ))

        try:
            conn.executemany(
                """INSERT INTO price_snapshots
                   (item_id, timestamp, buy_price, sell_price, buy_quantity, sell_quantity)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                rows,
            )
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Database error storing prices: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()

        return len(rows)

    def _store_items(self, items: list[dict]) -> int:
        """Upsert item metadata into items table."""
        conn = get_connection()
        rows = []

        for item in items:
            rows.append((
                item["id"],
                item.get("name", "Unknown"),
                item.get("rarity", ""),
                item.get("type", ""),
                item.get("level", 0),
                item.get("icon", ""),
            ))

        try:
            conn.executemany(
                """INSERT OR REPLACE INTO items
                   (item_id, name, rarity, type, level, icon_url)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                rows,
            )
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Database error storing items: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()

        return len(rows)

    @staticmethod
    def _batch(items: list, size: int):
        """Yield successive chunks of the given size."""
        for i in range(0, len(items), size):
            yield items[i : i + size]
