"""Entry point for the GW2 price collector with APScheduler.

Runs tiered polling:
  - Top 20 items every 15 minutes
  - Top 200 items every hour
"""

import asyncio
import logging
import signal
import sys

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from gw2trading.collectors.price_collector import PriceCollector
from gw2trading.collectors.tracked_items import TOP_20_ITEM_IDS, TOP_200_ITEM_IDS
from gw2trading.config import settings
from gw2trading.utils.logging import setup_logging

logger = logging.getLogger("gw2trading.collectors.price")

collector = PriceCollector()


async def collect_top20() -> None:
    """Collect prices for top 20 high-volume items."""
    await collector.collect_prices(TOP_20_ITEM_IDS)


async def collect_top200() -> None:
    """Collect prices for top 200 items."""
    await collector.collect_prices(TOP_200_ITEM_IDS)


async def initial_setup() -> None:
    """Fetch item metadata on first run, then do an immediate price collection."""
    all_ids = list(set(TOP_200_ITEM_IDS))
    await collector.fetch_and_store_item_metadata(all_ids)
    await collector.collect_prices(all_ids)


def main() -> None:
    setup_logging()
    logger.info("Starting GW2 Price Collector")
    logger.info(f"Database: {settings.db_path}")
    logger.info(f"Top 20 interval: {settings.price_poll_top20_interval}s")
    logger.info(f"Top 200 interval: {settings.price_poll_top200_interval}s")

    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        collect_top20,
        "interval",
        seconds=settings.price_poll_top20_interval,
        id="price_top20",
        name="Top 20 price collection",
    )

    scheduler.add_job(
        collect_top200,
        "interval",
        seconds=settings.price_poll_top200_interval,
        id="price_top200",
        name="Top 200 price collection",
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Run initial setup (metadata + first collection)
    loop.run_until_complete(initial_setup())
    logger.info("Initial collection complete. Scheduler starting...")

    scheduler.start()

    # Graceful shutdown
    def shutdown(signum, frame):
        logger.info("Shutting down...")
        scheduler.shutdown(wait=False)
        loop.run_until_complete(collector.close())
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        shutdown(None, None)


if __name__ == "__main__":
    main()
