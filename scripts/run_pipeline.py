"""Manual trigger for the RAG pipeline.

Usage:
    python scripts/run_pipeline.py
    python scripts/run_pipeline.py --trigger "New patch note: crafting update"
"""

import argparse
import asyncio
import logging
import sys

from gw2trading.rag.pipeline import RAGPipeline
from gw2trading.analysis.signal_ranker import SignalRanker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("gw2trading.scripts.run_pipeline")


async def main(trigger: str | None = None) -> None:
    """Run the RAG pipeline and print results."""
    logger.info("Starting RAG pipeline...")

    pipeline = RAGPipeline()
    output = await pipeline.generate_signals(trigger=trigger)

    logger.info(f"Generated {len(output.signals)} signal(s)")
    print("\n" + "=" * 60)
    print(f"ANALYSIS SUMMARY: {output.analysis_summary}")
    print(f"TIMESTAMP: {output.timestamp}")
    print("=" * 60)

    for i, signal in enumerate(output.signals, 1):
        print(f"\n--- Signal {i} ---")
        print(f"  Items:       {', '.join(signal.affected_items)}")
        print(f"  Direction:   {signal.direction}")
        print(f"  Confidence:  {signal.confidence:.0%}")
        print(f"  Horizon:     {signal.time_horizon}")
        print(f"  Reasoning:   {signal.reasoning}")
        if signal.expected_move_pct is not None:
            print(f"  Expected Move: {signal.expected_move_pct:+.1f}%")
        print(f"  Sources:     {', '.join(signal.source_documents)}")

    # Rank, filter, and store signals
    print("\n" + "=" * 60)
    print("RANKING & FILTERING...")
    print("=" * 60)

    ranker = SignalRanker()
    stored = ranker.rank_signals(output, trigger=trigger)
    print(f"\n{len(output.signals)} raw signal(s) → {len(stored)} stored after filtering")

    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the GW2 trading RAG pipeline")
    parser.add_argument(
        "--trigger",
        type=str,
        default=None,
        help="Trigger event description (default: scheduled daily scan)",
    )
    args = parser.parse_args()

    asyncio.run(main(trigger=args.trigger))
