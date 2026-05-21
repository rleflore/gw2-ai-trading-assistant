"""Trading Signals page — active and historical signals from the RAG pipeline."""

import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta

from gw2trading.db.database import get_connection
from gw2trading.analysis.accuracy_tracker import AccuracyTracker

# Item keywords to match in Reddit posts for community buzz
MARKET_ITEM_KEYWORDS = [
    "mystic coin", "ecto", "ectoplasm", "precursor", "legendary",
    "amalgamated", "t6", "tier 6", "orichalcum", "mystic clover",
    "trading post", "tp price", "gold", "gem", "crafting",
    "ascended", "mithril", "elder wood", "deldrimor", "elonian",
    "mystic forge", "salvage", "drop rate", "farm", "meta event",
]


def render():
    st.title("Trading Signals")
    st.markdown(
        '<p style="font-size: 0.9em; color: #FAF9F6;">'
        "AI-generated trading recommendations from the RAG pipeline.<br>"
        "These signals are based on real-time market data and community sentiment.</p>",
        unsafe_allow_html=True,
    )

    # Accuracy stat right-aligned above tabs
    _render_accuracy_stats()

    # Tabs for active vs history
    tab_active, tab_history = st.tabs(["Active Signals", "Signal History"])

    with tab_active:
        _render_active_signals()
        _render_community_buzz()

    with tab_history:
        _render_signal_history()


def _render_accuracy_stats():
    """Show model accuracy summary at top of page."""
    tracker = AccuracyTracker()
    stats = tracker.get_accuracy_stats()

    if stats["total"] == 0:
        return

    # Get the most recent validation date
    conn = get_connection()
    last_validated = conn.execute(
        "SELECT MAX(validated_at) FROM signals WHERE validated_at IS NOT NULL"
    ).fetchone()[0]
    conn.close()
    last_date = last_validated[:10] if last_validated else "—"

    st.markdown(
        f'<div style="position: absolute; right: 3rem; top: -3rem; text-align: center; z-index: 999;">'
        f'<div style="font-size: 1.2em; font-weight: bold;">Model Accuracy</div>'
        f'<div style="font-size: 1.5em;">{stats["accuracy_pct"]:.0f}%</div>'
        f'<div style="font-size: 0.8em; color: gray;">Last updated: {last_date}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_active_signals():
    """Show currently active signals as cards."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT item_name, direction, confidence, reasoning, time_horizon,
                  expected_move_pct, source_documents, trigger_event, timestamp
           FROM signals
           WHERE status = 'active'
           ORDER BY confidence DESC"""
    ).fetchall()
    conn.close()

    if not rows:
        st.info("No active signals. The pipeline runs daily at 10 AM.")
        return

    st.markdown(f"**{len(rows)} active signal(s)**")

    for row in rows:
        item_name, direction, confidence, reasoning, time_horizon, \
            expected_move_pct, source_documents, trigger_event, timestamp = row

        # Color and arrow based on direction
        if direction == "bullish":
            color = "#4caf50"
            arrow = "↑"
        elif direction == "bearish":
            color = "#f44336"
            arrow = "↓"
        else:
            color = "#ffeb3b"
            arrow = "→"

        with st.container():
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
            with col1:
                st.markdown(f"**{arrow} {item_name}**")
            with col2:
                st.markdown(f"Direction: **{direction}**")
            with col3:
                st.markdown(f"Confidence: **{confidence:.0%}**")
            with col4:
                move_str = f"{expected_move_pct:+.0f}%" if expected_move_pct else "—"
                st.markdown(f"Expected: **{move_str}** in {time_horizon}")

            st.markdown(f"*{reasoning}*")
            st.caption(f"Trigger: {trigger_event} | Generated: {timestamp}")
            st.markdown("---")


def _render_signal_history():
    """Show past signals with their status."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT item_name, direction, confidence, reasoning, time_horizon,
                  expected_move_pct, status, trigger_event, timestamp
           FROM signals
           ORDER BY timestamp DESC
           LIMIT 50"""
    ).fetchall()
    conn.close()

    if not rows:
        st.info("No signal history yet.")
        return

    df = pd.DataFrame(rows, columns=[
        "Item", "Direction", "Confidence", "Reasoning", "Horizon",
        "Expected Move %", "Status", "Trigger", "Timestamp"
    ])
    df["Confidence"] = df["Confidence"].apply(lambda x: f"{x:.0%}")
    df["Expected Move %"] = df["Expected Move %"].apply(
        lambda x: f"{x:+.0f}%" if pd.notna(x) else "—"
    )

    # Status filter
    statuses = ["All"] + sorted(df["Status"].unique().tolist())
    selected_status = st.selectbox("Filter by status", statuses)
    if selected_status != "All":
        df = df[df["Status"] == selected_status]

    st.dataframe(
        df[["Timestamp", "Item", "Direction", "Confidence", "Expected Move %", "Horizon", "Status"]],
        use_container_width=True,
        hide_index=True,
    )


def _render_community_buzz():
    """Show top Reddit posts mentioning market-relevant items."""
    st.markdown("---")
    st.subheader("Community Buzz")

    conn = get_connection()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    rows = conn.execute(
        """SELECT title, timestamp, upvotes, url
           FROM reddit_posts
           WHERE timestamp > ?
           ORDER BY timestamp DESC
           LIMIT 50""",
        (cutoff,)
    ).fetchall()
    conn.close()

    # Filter to posts mentioning market items
    relevant = []
    for title, timestamp, upvotes, url in rows:
        title_lower = title.lower()
        if any(kw in title_lower for kw in MARKET_ITEM_KEYWORDS):
            post_date = datetime.fromisoformat(timestamp).strftime("%b %d")
            fade_date = (datetime.fromisoformat(timestamp) + timedelta(days=7)).strftime("%b %d")
            relevant.append({
                "title": title,
                "date": post_date,
                "fades": fade_date,
                "upvotes": upvotes,
                "url": url,
            })
        if len(relevant) >= 3:
            break

    if not relevant:
        st.caption("No market-relevant community discussion this week.")
    else:
        for post in relevant:
            st.markdown(f"• **{post['title']}** — {post['date']} (fades {post['fades']}) [view →]({post['url']})")

