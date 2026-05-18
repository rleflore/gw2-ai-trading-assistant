"""Price context module — computes market analytics for LLM prompts."""
 
import logging
from datetime import datetime, timezone, timedelta

import pandas as pd
 
from gw2trading.db.database import get_connection
 
logger = logging.getLogger("gw2trading.analysis.price_context")

class PriceContext:
    """Computes market analytics for LLM prompts."""
 
    def get_market_context(self, item_ids: list[int] | None = None) -> str:
        """Build a formatted market context string for all tracked items.
         
        Returns a multi-line string like:
            MARKET CONTEXT:
            - Mystic Coin: 2g 45s (↑12% 7d, ↑3% 24h, volume: high)
            - Glob of Ectoplasm: 35s (↓5% 7d, flat 24h, volume: declining)
        """
        
        df = self._load_price_data(item_ids)
        context_lines = ["MARKET CONTEXT:"]
        for item_id, group in df.groupby("item_id"):
            name = group["name"].iloc[0]
            analytics = self._compute_item_analytics(group)
            price_str = self._format_price(analytics["current_price"])
            change_7d_str = self._format_change(analytics["change_7d"])
            change_24h_str = self._format_change(analytics["change_24h"])
            volume_str = analytics["volume_trend"]
            line = f"- {name}: {price_str} ({change_7d_str} 7d, {change_24h_str} 24h, volume: {volume_str})"
            if analytics["anomaly"]:
                line += " — ANOMALY"
            context_lines.append(line)

        return "\n".join(context_lines)


        
    def _load_price_data(self, item_ids: list[int] | None = None, days: int = 30) -> pd.DataFrame:
        """Load price snapshots from last N days into a DataFrame.
         
         Columns: item_id, timestamp, buy_price, sell_price, buy_quantity, sell_quantity
         Also joins item name from items table.
         """
        
        conn = get_connection()
        rows = []
        try:
            query = """
                SELECT ps.item_id, ps.timestamp, ps.buy_price, ps.sell_price, ps.buy_quantity, ps.sell_quantity, i.name
                FROM price_snapshots ps
                JOIN items i ON ps.item_id = i.item_id
                WHERE ps.timestamp > ?
            """
            params = [(datetime.now(timezone.utc) - timedelta(days=days)).isoformat()]
            if item_ids:
                query += " AND ps.item_id IN ({})".format(','.join('?' for _ in item_ids))
                params.extend(item_ids)
            query += " ORDER BY ps.item_id, ps.timestamp"
            result = conn.execute(query, params)
            rows = result.fetchall()
        except Exception as e:
            logger.error("Error loading price data: %s", e)
        finally:
            conn.close()
        df = pd.DataFrame(rows, columns=["item_id", "timestamp", "buy_price", "sell_price", "buy_quantity", "sell_quantity", "name"])
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df


    def _compute_item_analytics(self, df: pd.DataFrame) -> dict:
        """Compute analytics for a single item's price history.      
         Returns dict with:
             - current_price (sell_price of latest snapshot)
             - change_1h, change_24h, change_7d (% change floats)
             - volume_trend: "high" | "normal" | "declining"
             - spread: current buy/sell spread as %
             - sma_7d, sma_30d: simple moving averages
             - anomaly: bool (True if >20% move in 24h)
         """
        
        latest = df.iloc[-1]
        cur_price = latest["sell_price"]
        now = df["timestamp"].max()

        target_1h = now - timedelta(hours=1)
        idx_1h = (df["timestamp"] - target_1h).abs().idxmin()
        price_1h = df.loc[idx_1h, "sell_price"]
        change_1h = (cur_price - price_1h) / price_1h * 100 if price_1h > 0 else 0

        target_24h = now - timedelta(hours=24)
        idx_24h = (df["timestamp"] - target_24h).abs().idxmin()
        price_24h = df.loc[idx_24h, "sell_price"]
        change_24h = (cur_price - price_24h) / price_24h * 100 if price_24h > 0 else 0

        target_7d = now - timedelta(days=7)
        idx_7d = (df["timestamp"] - target_7d).abs().idxmin()
        price_7d = df.loc[idx_7d, "sell_price"]
        change_7d = (cur_price - price_7d) / price_7d * 100 if price_7d > 0 else 0

        recent_volume = df[df["timestamp"] > (now - timedelta(days=1))]["buy_quantity"].mean()
        recent_volume = recent_volume if pd.notna(recent_volume) else 0
        baseline_volume = df[(df["timestamp"] > (now - timedelta(days=30))) & (df["timestamp"] <= (now - timedelta(days=1))) ]["buy_quantity"].mean()
        baseline_volume = baseline_volume if pd.notna(baseline_volume) else recent_volume
        volume_trend = self._classify_volume(recent_volume, baseline_volume)
        spread = (latest["sell_price"] - latest["buy_price"]) / latest["sell_price"] * 100 if latest["sell_price"] > 0 else 0
        sma_7d = df[df["timestamp"] > (now - timedelta(days=7))]["sell_price"].mean()
        sma_30d = df[df["timestamp"] > (now - timedelta(days=30))]["sell_price"].mean()
        anomaly = abs(change_24h) > 20

        return {
            "current_price": cur_price,
            "change_1h": change_1h,
            "change_24h": change_24h,
            "change_7d": change_7d,
            "volume_trend": volume_trend,
            "spread": spread,
            "sma_7d": sma_7d,
            "sma_30d": sma_30d,
            "anomaly": anomaly
        }


    def _format_price(self, copper: int) -> str:
        """Convert copper to human-readable gold/silver/copper."""

        gold = copper // 10000
        silver = (copper % 10000) // 100
        copper_rem = copper % 100
        parts = []
        if gold > 0:
            parts.append(f"{gold}g")
        if silver > 0:
            parts.append(f"{silver}s")
        if copper_rem > 0 or not parts:
            parts.append(f"{copper_rem}c")
        return " ".join(parts)

    def _format_change(self, pct: float) -> str:
        """Format a % change with arrow."""

        if abs(pct) < 0.5:
            return "flat"
        elif pct > 0:
            return f"↑{pct:.1f}%"
        else:
            return f"↓{abs(pct):.1f}%"
        

    def _classify_volume(self, recent_avg: float, baseline_avg: float) -> str:
        """Classify volume trend based on recent vs baseline average."""
      
        ratio = (recent_avg / baseline_avg) if baseline_avg > 0 else float('inf')
        if ratio > 1.3:
            return "high"
        elif ratio < 0.7:
            return "declining"
        else:
            return "normal"