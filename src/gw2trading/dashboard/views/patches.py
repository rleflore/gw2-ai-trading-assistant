"""Patch Analysis page — recent patch notes with LLM impact analysis."""

import streamlit as st
import pandas as pd

from gw2trading.db.database import get_connection


def render():
    st.title("Patch Analysis")
    st.caption("Recent Guild Wars 2 patch notes with AI-generated impact analysis")

    conn = get_connection()
    rows = conn.execute(
        """SELECT date, title, full_text, source_url
           FROM patch_notes
           ORDER BY date DESC
           LIMIT 20"""
    ).fetchall()

    # Get signals triggered by patch notes
    signal_rows = conn.execute(
        """SELECT trigger_event, item_name, direction, confidence, expected_move_pct, reasoning
           FROM signals
           WHERE trigger_event LIKE 'Patch notes%'
           ORDER BY timestamp DESC"""
    ).fetchall()
    conn.close()

    if not rows:
        st.warning("No patch notes collected yet. Run the collectors first.")
        return

    # Build a lookup: date -> signals
    signals_by_date = {}
    for sig in signal_rows:
        trigger = sig[0] or ""
        if "(" in trigger and ")" in trigger:
            sig_date = trigger.split("(")[1].split(")")[0]
            if sig_date not in signals_by_date:
                signals_by_date[sig_date] = []
            signals_by_date[sig_date].append({
                "item": sig[1],
                "direction": sig[2],
                "confidence": sig[3],
                "move": sig[4],
                "reasoning": sig[5],
            })

    # Only show patches that generated signals
    relevant_rows = [row for row in rows if row[0] in signals_by_date]

    if not relevant_rows:
        st.info("No market-relevant patch notes yet. Patches that trigger trading signals will appear here.")
        return

    st.markdown(f"**{len(relevant_rows)} market-relevant patch note(s)**")
    st.markdown("---")

    for row in relevant_rows:
        date, title, full_text, source_url = row

        # Clean up title
        display_title = title.replace("Game updates/", "Game Update — ")
        display_title = display_title.replace("<noinclude>", "").replace("</noinclude>", "").strip()

        # Extract first line as category (e.g., "Bug Fixes", "Balance Changes")
        lines = full_text.strip().split("\n")
        # Clean noinclude tags from content
        cleaned_lines = []
        for line in lines:
            line = line.replace("<noinclude>", "").replace("</noinclude>", "").strip()
            if line:
                cleaned_lines.append(line)

        category = cleaned_lines[0] if cleaned_lines else ""
        body = "\n".join(cleaned_lines[1:]) if len(cleaned_lines) > 1 else ""

        with st.expander(f"{date} — {display_title}"):
            # Category header
            if category:
                st.markdown(f"**{category}**")
                st.markdown("---")

            # AI Analysis
            if date in signals_by_date:
                st.markdown("**AI Impact Analysis:**")
                for sig in signals_by_date[date]:
                    arrow = "↑" if sig["direction"] == "bullish" else "↓" if sig["direction"] == "bearish" else "→"
                    move_str = f"{sig['move']:+.0f}%" if sig["move"] else ""
                    st.markdown(f"- {arrow} **{sig['item']}** — {sig['direction']} ({sig['confidence']:.0%}) {move_str}")
                    st.markdown(f"  *{sig['reasoning']}*")
                st.markdown("---")

            # Patch content
            if len(body) > 2000:
                st.markdown(body[:2000] + "...")
                st.caption("(Truncated)")
            else:
                st.markdown(body)

            if source_url:
                st.markdown(f"[View on Wiki]({source_url})")

