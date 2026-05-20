"""Signal accuracy tracker — validates predictions against actual price movements.

Runs daily after the pipeline. Finds expired signals, checks actual prices,
and marks them as validated or invalidated.
"""

import logging
from datetime import datetime, timezone, timedelta

from gw2trading.db.database import get_connection

logger = logging.getLogger("gw2trading.analysis.accuracy_tracker")


class AccuracyTracker:
    """Checks expired signals against actual price data."""

    def check_expired_signals(self) -> None:
        expired_signals = self._get_expired_signals()
        for signal in expired_signals:
            price_at_signal = self._get_price_at_time(signal["item_name"], signal["timestamp"])
            current_price = self._get_current_price(signal["item_name"])
            if price_at_signal is None or current_price is None:
                logger.warning(f"Could not find price data for {signal['item_name']} at signal time or now, skipping validation")
                continue
            actual_move_pct = ((current_price - price_at_signal) / price_at_signal) * 100
            status = self._validate_signal(signal, actual_move_pct)
            self._update_signal_status(signal["id"], status, actual_move_pct)


    def _get_expired_signals(self) -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            """SELECT id, item_name, direction, confidence, time_horizon, timestamp
               FROM signals
               WHERE status = 'active'"""
        ).fetchall()
        conn.close()
        signals = []
        for row in rows:
            signals.append({
                "id": row[0],
                "item_name": row[1],
                "direction": row[2],
                "confidence": row[3],
                "time_horizon": row[4],
                "timestamp": row[5],
            })
        expired_signals = []
        now = datetime.now(timezone.utc)
        for signal in signals:
            horizon_days = self._parse_horizon_days(signal["time_horizon"])
            signal_time = datetime.fromisoformat(signal["timestamp"]).replace(tzinfo=timezone.utc)
            if signal_time + timedelta(days=horizon_days) <= now:
                expired_signals.append(signal)
        return expired_signals

    def _parse_horizon_days(self, time_horizon: str) -> int:
        if "day" in time_horizon:
            num_part = time_horizon.split("day")[0].strip()
            max_days = int(num_part.split("-")[-1])
            return max_days
        elif "week" in time_horizon:
            num_part = time_horizon.split("week")[0].strip()
            max_weeks = int(num_part.split("-")[-1])
            return max_weeks * 7
        else:
            raise ValueError(f"Unknown time_horizon format: {time_horizon}")

    def _get_price_at_time(self, item_name: str, timestamp: str) -> int | None:
        conn = get_connection()
        row = conn.execute(
            """SELECT ps.sell_price FROM price_snapshots ps
               JOIN items i ON ps.item_id = i.item_id
               WHERE i.name = ? AND ps.timestamp <= ?
               ORDER BY ps.timestamp DESC LIMIT 1""",
            (item_name, timestamp)
        ).fetchone()
        conn.close()
        return row[0] if row else None

    def _get_current_price(self, item_name: str) -> int | None:
        conn = get_connection()
        row = conn.execute(
            """SELECT ps.sell_price FROM price_snapshots ps
               JOIN items i ON ps.item_id = i.item_id
               WHERE i.name = ?
               ORDER BY ps.timestamp DESC LIMIT 1""",
            (item_name,)
        ).fetchone()
        conn.close()
        return row[0] if row else None
    
        
    def _validate_signal(self, signal: dict, actual_move_pct: float) -> str:
        if signal["direction"] == "bullish" and actual_move_pct > 0:
            return "validated"
        elif signal["direction"] == "bearish" and actual_move_pct < 0:
            return "validated"
        else:
            return "invalidated"
        

    def _update_signal_status(self, signal_id: int, status: str, actual_move_pct: float) -> None:
        conn = get_connection()
        conn.execute(
            """UPDATE signals
               SET status = ?, actual_move_pct = ?, validated_at = datetime('now')
               WHERE id = ?""",
            (status, actual_move_pct, signal_id)
        )
        conn.commit()
        conn.close()

    def get_accuracy_stats(self) -> dict:
        conn = get_connection()
        rows = conn.execute(
            """SELECT status, COUNT(*) FROM signals
               WHERE status IN ('validated', 'invalidated')
               GROUP BY status"""
        ).fetchall()
        conn.close()
        stats = {"total": 0, "correct": 0}
        for row in rows:
            status, count = row
            stats["total"] += count
            if status == "validated":
                stats["correct"] += count
        stats["accuracy_pct"] = (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0.0
        return stats
