"""Unified entry point for all GW2 data collectors.
 
 Schedules:
   - Price (Top 20): every 15 min
   - Price (Top 200): every 1 hour
   - Wiki patch notes: every 1 hour
   - Reddit posts: every 1 hour
 """
 
import asyncio
import logging
import signal
import sys
 
from apscheduler.schedulers.asyncio import AsyncIOScheduler
 
from gw2trading.collectors.price_collector import PriceCollector
from gw2trading.collectors.wiki_collector import WikiCollector
from gw2trading.collectors.reddit_collector import RedditCollector
from gw2trading.collectors.tracked_items import TOP_20_ITEM_IDS, TOP_200_ITEM_IDS
from gw2trading.config import settings
from gw2trading.utils.logging import setup_logging

logger = logging.getLogger("gw2trading")

# Initialize collectors
price_collector = PriceCollector()
wiki_collector = WikiCollector()
reddit_collector = RedditCollector()

# collect prices for top 20 items every 15 minutes
async def collect_prices_top_20() -> None:
    try:
        await price_collector.collect_prices(TOP_20_ITEM_IDS)
    except Exception as e:
        logger.error(f"Error collecting top 20 prices: {e}")

# collect prices for top 200 items every hour
async def collect_prices_top_200() -> None:
    try:
        await price_collector.collect_prices(TOP_200_ITEM_IDS)
    except Exception as e:
        logger.error(f"Error collecting top 200 prices: {e}")

# collect wiki patch notes every hour
async def collect_wiki_patch_notes() -> None:
    try:
        await wiki_collector.collect_patch_notes()
    except Exception as e:
        logger.error(f"Error collecting wiki patch notes: {e}")

# collect reddit posts every hour
async def collect_reddit_posts() -> None:
    try:
        await reddit_collector.collect_posts()
    except Exception as e:
        logger.error(f"Error collecting reddit posts: {e}")


async def initial_setup() -> None:
    """Run on startup: fetch metadata + one immediate collection of everything"""
    logger.info("Running initial setup...")
    # Fetch metadata for top 200 items (ensures we have names for all tracked items)
    await price_collector.fetch_and_store_item_metadata(TOP_200_ITEM_IDS)
    await collect_prices_top_200()
    await collect_wiki_patch_notes()
    await collect_reddit_posts()
    


def main() -> None:
    setup_logging()

    logger.info("Starting GW2 Trading Post Data Collectors")
    logger.info(f"Database path: {settings.db_path}")
    logger.info(f"Price poll interval (top 20): {settings.price_poll_top20_interval} seconds")
    logger.info(f"Price poll interval (top 200): {settings.price_poll_top200_interval} seconds")
    logger.info(f"Wiki poll interval: {settings.wiki_poll_interval} seconds")
    logger.info(f"Reddit poll interval: {settings.reddit_poll_interval} seconds")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(collect_prices_top_20, "interval", seconds=settings.price_poll_top20_interval, next_run_time=None)
    scheduler.add_job(collect_prices_top_200, "interval", seconds=settings.price_poll_top200_interval, next_run_time=None)
    scheduler.add_job(collect_wiki_patch_notes, "interval", seconds=settings.wiki_poll_interval, next_run_time=None)
    scheduler.add_job(collect_reddit_posts, "interval", seconds=settings.reddit_poll_interval, next_run_time=None)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def _start():
        await initial_setup()
        logger.info("Initial setup complete. Starting scheduler...")
        scheduler.start()

    loop.run_until_complete(_start())

    def handle_shutdown(signum, frame) -> None:
        logger.info("Shutting down collectors...")
        scheduler.shutdown(wait=False)
        loop.run_until_complete(price_collector.close())
        loop.run_until_complete(wiki_collector.close())
        loop.run_until_complete(reddit_collector.close())
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        handle_shutdown(None, None)
    finally:
        loop.close()
    
if __name__ == "__main__":
    main()