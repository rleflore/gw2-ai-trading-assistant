"""Market Overview page — live prices, changes, volume for tracked items."""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timezone, timedelta

from gw2trading.db.database import get_connection


def render():
    st.title("Market Overview")
    st.markdown(
        '<p style="font-size: 0.85em; color: rgba(49,51,63,0.6);">'
        "Real-time price tracking for GW2 Trading Post items.<br>"
        "Shows 24h/7d price changes, volume trends, and flags anomalies (>20% moves).</p>",
        unsafe_allow_html=True,
    )

    df = _load_market_data()

    if df.empty:
        st.warning("No price data available yet. Run the collectors first.")
        return

    # Summary metrics row
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Tracked Items", len(df["name"].unique()))
    with col2:
        anomalies = df[df["change_24h"].abs() > 20]
        st.metric("Anomalies (>20% 24h)", len(anomalies))
    with col3:
        latest = df["timestamp"].max()
        st.metric("Last Update", latest.strftime("%H:%M") if pd.notna(latest) else "—")

    st.markdown("---")

    # Price table
    st.subheader("Current Prices")
    table_df = _build_price_table(df)
    st.dataframe(
        table_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "24h Change": st.column_config.NumberColumn(format="%.1f%%"),
            "7d Change": st.column_config.NumberColumn(format="%.1f%%"),
            "Sell Price": st.column_config.TextColumn(),
            "Buy Price": st.column_config.TextColumn(),
        },
    )

    st.markdown("---")

    # Price chart for selected item
    st.subheader("Price History")
    items = sorted(df["name"].unique())
    selected_item = st.selectbox("Search item", items, index=None, placeholder="Type to search...")

    if selected_item:
        item_df = df[df["name"] == selected_item].sort_values("timestamp")
        fig = px.line(
            item_df,
            x="timestamp",
            y=["sell_price_gold", "buy_price_gold"],
            labels={"value": "Price (gold)", "timestamp": "Time", "variable": "Type"},
            title=f"{selected_item} — Price History",
        )
        fig.update_layout(hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)


def _load_market_data() -> pd.DataFrame:
    """Load recent price data for all tracked items."""
    conn = get_connection()
    query = """
        SELECT ps.item_id, ps.timestamp, ps.buy_price, ps.sell_price,
               ps.buy_quantity, ps.sell_quantity, i.name
        FROM price_snapshots ps
        JOIN items i ON ps.item_id = i.item_id
        WHERE ps.timestamp > datetime('now', '-7 days')
        ORDER BY ps.timestamp DESC
    """
    rows = conn.execute(query).fetchall()
    conn.close()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=[
        "item_id", "timestamp", "buy_price", "sell_price",
        "buy_quantity", "sell_quantity", "name"
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="mixed", utc=True)
    # Convert copper to gold for display
    df["sell_price_gold"] = df["sell_price"] / 10000
    df["buy_price_gold"] = df["buy_price"] / 10000

    # Compute 24h and 7d changes per item
    df["change_24h"] = 0.0
    df["change_7d"] = 0.0
    now = datetime.now(timezone.utc)
    for item_id, group in df.groupby("item_id"):
        current = group["sell_price"].iloc[0]  # Most recent (sorted DESC)
        # 24h change
        day_ago = group[group["timestamp"] < now - timedelta(hours=24)]
        if not day_ago.empty:
            old_price = day_ago["sell_price"].iloc[0]
            if old_price > 0:
                df.loc[group.index, "change_24h"] = ((current - old_price) / old_price) * 100
        # 7d change
        week_ago = group[group["timestamp"] < now - timedelta(days=7)]
        if not week_ago.empty:
            old_price = week_ago["sell_price"].iloc[0]
            if old_price > 0:
                df.loc[group.index, "change_7d"] = ((current - old_price) / old_price) * 100

    return df


def _build_price_table(df: pd.DataFrame) -> pd.DataFrame:
    """Build a summary table with one row per item."""
    latest = df.sort_values("timestamp").drop_duplicates("name", keep="last")
    table = latest[["name"]].copy()
    table["Sell Price"] = latest["sell_price"].apply(_format_price)
    table["Buy Price"] = latest["buy_price"].apply(_format_price)
    table["24h Change"] = latest["change_24h"].values
    table["7d Change"] = latest["change_7d"].values
    table["Buy Volume"] = latest["buy_quantity"].values
    table["Sell Volume"] = latest["sell_quantity"].values
    table = table.rename(columns={"name": "Item"})
    table = table.sort_values("24h Change", ascending=False)
    return table.reset_index(drop=True)


def _format_price(copper: int) -> str:
    """Convert copper to gold/silver/copper display."""
    gold = copper // 10000
    silver = (copper % 10000) // 100
    cop = copper % 100
    if gold > 0:
        return f"{gold}g {silver}s {cop}c"
    elif silver > 0:
        return f"{silver}s {cop}c"
    else:
        return f"{cop}c"
