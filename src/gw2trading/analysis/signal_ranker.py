"""Signal ranking and filtering module.

Takes raw LLM signals and filters them into actionable recommendations.
Only signals that pass confidence, profitability, and deduplication checks
get stored in the database.
"""

import json
import logging
from datetime import datetime, timezone, timedelta

from gw2trading.db.database import get_connection
from gw2trading.rag.models import TradingSignal, PipelineOutput

logger = logging.getLogger("gw2trading.analysis.signal_ranker")

MIN_CONFIDENCE = 0.75
MIN_MOVE_PCT = 20.0


class SignalRanker:
    """Filters, ranks, and stores trading signals."""

    def rank_signals(self, output: PipelineOutput, trigger: str | None = None) -> list[TradingSignal]:
        for signal in output.signals:
            if not self._passes_confidence(signal):
                logger.info(f"Signal for {signal.affected_items} failed confidence check ({signal.confidence:.0%})")
                continue
            if not self._passes_profitability(signal):
                logger.info(f"Signal for {signal.affected_items} failed profitability check (expected move {signal.expected_move_pct:+.1f}%)")
                continue
            if self._is_duplicate(signal):
                logger.info(f"Signal for {signal.affected_items} is a duplicate of an active signal, skipping")
                continue
            conflicting_signal_ids = self._detect_conflicts(signal)
            if conflicting_signal_ids:
                logger.info(f"Signal for {signal.affected_items} conflicts with active signals {conflicting_signal_ids}, marking them as superseded")
                self._mark_superseded(conflicting_signal_ids)
            self._store_signal(signal, trigger)
        conn = get_connection()
        results = conn.execute(
            "SELECT item_name, direction, confidence, reasoning, time_horizon, expected_move_pct, source_documents FROM signals WHERE status = 'active' ORDER BY confidence DESC"
        ).fetchall()
        conn.close()
        return results
    

    def _passes_confidence(self, signal: TradingSignal) -> bool:
        return signal.confidence >= MIN_CONFIDENCE

    def _passes_profitability(self, signal: TradingSignal) -> bool:
        if signal.expected_move_pct is None:
            return True
        return abs(signal.expected_move_pct) >= MIN_MOVE_PCT

    def _is_duplicate(self, signal: TradingSignal) -> bool:
        conn = get_connection()
        cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        results = conn.execute(
            "SELECT COUNT(*) FROM signals WHERE item_name IN ({}) AND direction = ? AND timestamp > ? AND status = 'active'".format(
                ",".join("?" for _ in signal.affected_items)
            ),
            (*signal.affected_items, signal.direction, cutoff_time)
        ).fetchone()
        conn.close()
        return results[0] > 0

    def _detect_conflicts(self, signal: TradingSignal) -> list[int]:
        conn = get_connection()
        results = conn.execute(
            "SELECT id FROM signals WHERE item_name IN ({}) AND direction != ? AND status = 'active'".format(
                ",".join("?" for _ in signal.affected_items)
            ),
            (*signal.affected_items, signal.direction)
        ).fetchall()
        conn.close()
        return [row[0] for row in results]

    def _mark_superseded(self, signal_ids: list[int]) -> None:
        """Mark conflicting signals as 'superseded' in the DB."""
        conn = get_connection()
        conn.execute(
            "UPDATE signals SET status = 'superseded' WHERE id IN ({})".format(
                ",".join("?" for _ in signal_ids)
            ),
            signal_ids
        )
        conn.commit()
        conn.close()

    def _store_signal(self, signal: TradingSignal, trigger: str | None = None) -> None:
        """Insert a validated signal into the signals table."""
        conn = get_connection()
        for item in signal.affected_items:
            conn.execute(
                "INSERT INTO signals (item_name, direction, confidence, reasoning, time_horizon, expected_move_pct, source_documents, trigger_event) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    item,
                    signal.direction,
                    signal.confidence,
                    signal.reasoning,
                    signal.time_horizon,
                    signal.expected_move_pct,
                    json.dumps(signal.source_documents),
                    trigger
                )
            )
        conn.commit()
        conn.close()
