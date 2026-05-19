"""Backfill historical price data from the DataWars2 API.

Usage:
    # Backfill tracked items (Top 200) — takes ~5 minutes
    python scripts/backfill_history.py

    # Backfill with date range
    python scripts/backfill_history.py --start 2024-01-01 --end 2025-12-31

    # Also fetch full item catalog (all ~27K item names)
    python scripts/backfill_history.py --catalog

    # Run retention cleanup (delete stale non-tracked history older than 90 days)
    python scripts/backfill_history.py --cleanup
"""

import argparse
import asyncio
import logging
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent / "src"))

from gw2trading.collectors.datawars2_collector import DataWars2Collector
from gw2trading.collectors.tracked_items import TOP_200_ITEM_IDS
from gw2trading.utils.logging import setup_logging

logger = logging.getLogger("gw2trading")


async def run_backfill(args: argparse.Namespace) -> None:
    collector = DataWars2Collector()

    try:
        if args.catalog:
            logger.info("Fetching full item catalog...")
            count = await collector.fetch_full_catalog()
            logger.info(f"Catalog complete: {count} items stored")

        if args.cleanup:
            logger.info("Running retention cleanup...")
            deleted = collector.cleanup_stale_history(retention_days=args.retention_days)
            logger.info(f"Cleanup complete: {deleted} rows deleted")
            return

        logger.info(f"Backfilling history for {len(TOP_200_ITEM_IDS)} tracked items...")
        total = await collector.backfill_history(
            item_ids=TOP_200_ITEM_IDS,
            start=args.start,
            end=args.end,
        )
        logger.info(f"Backfill complete: {total} total history rows stored")

    finally:
        await collector.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill historical price data from DataWars2")
    parser.add_argument("--start", type=str, default=None, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, default=None, help="End date (YYYY-MM-DD)")
    parser.add_argument("--catalog", action="store_true", help="Fetch full item catalog first")
    parser.add_argument("--cleanup", action="store_true", help="Run retention cleanup instead")
    parser.add_argument(
        "--retention-days", type=int, default=90, help="Days to keep non-tracked history (default: 90)"
    )
    args = parser.parse_args()

    setup_logging()
    asyncio.run(run_backfill(args))


if __name__ == "__main__":
    main()
