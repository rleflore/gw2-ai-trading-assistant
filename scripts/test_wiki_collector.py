import asyncio
from gw2trading.collectors.wiki_collector import WikiCollector


async def main():
    collector = WikiCollector()
    count = await collector.collect_patch_notes(since="2026-05-01")
    print(f"Collected {count} patch notes")

asyncio.run(main())