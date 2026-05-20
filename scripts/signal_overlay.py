"""Signal overlay — transparent always-on-top HUD showing latest trading signals.

Reads the most recent active signals from the DB and displays them
in a small draggable overlay window suitable for borderless windowed GW2.
"""

import tkinter as tk
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from gw2trading.db.database import get_connection


# Overlay styling
BG_COLOR = "#1a1a2e"
TEXT_COLOR = "#e0e0e0"
HEADER_COLOR = "#00d4aa"
BULLISH_COLOR = "#4caf50"
BEARISH_COLOR = "#f44336"
NEUTRAL_COLOR = "#ffeb3b"
FONT_FAMILY = "Consolas"
OPACITY = 0.9
AUTO_HIDE_SECONDS = 60

POSITION_FILE = Path(__file__).parent.parent / "data" / "overlay_position.json"


def get_latest_signals() -> list[dict]:
    """Fetch active signals from the last 24 hours."""
    conn = get_connection()
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    rows = conn.execute(
        """SELECT item_name, direction, confidence, expected_move_pct, time_horizon, timestamp
           FROM signals
           WHERE status = 'active' AND timestamp > ?
           ORDER BY confidence DESC
           LIMIT 8""",
        (cutoff,)
    ).fetchall()
    conn.close()

    signals = []
    for row in rows:
        signals.append({
            "item_name": row[0],
            "direction": row[1],
            "confidence": row[2],
            "expected_move_pct": row[3],
            "time_horizon": row[4],
            "timestamp": row[5],
        })
    return signals


def format_signal_line(signal: dict) -> tuple[str, str]:
    """Format a signal into a display line and return (text, color)."""
    direction = signal["direction"]
    if direction == "bullish":
        arrow = "↑"
        color = BULLISH_COLOR
    elif direction == "bearish":
        arrow = "↓"
        color = BEARISH_COLOR
    else:
        arrow = "→"
        color = NEUTRAL_COLOR

    name = signal["item_name"][:16].ljust(16)
    conf = f"{signal['confidence']:.0%}"
    move = f"{signal['expected_move_pct']:+.0f}%" if signal["expected_move_pct"] else "  —"
    horizon = signal["time_horizon"] or ""

    line = f" {arrow} {name} {conf}  {move}  {horizon}"
    return line, color


class SignalOverlay:
    """Transparent always-on-top overlay window."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GW2 Signals")
        self.root.overrideredirect(True)  # Borderless
        self.root.attributes("-topmost", True)  # Always on top
        self.root.attributes("-alpha", OPACITY)  # Transparency
        self.root.configure(bg=BG_COLOR)

        # Position: load saved position or default to top-right
        pos = self._load_position()
        if pos:
            self.root.geometry(f"+{pos['x']}+{pos['y']}")
        else:
            screen_w = self.root.winfo_screenwidth()
            self.root.geometry(f"+{screen_w - 420}+40")

        # Make window draggable
        self._drag_x = 0
        self._drag_y = 0
        self.root.bind("<Button-1>", self._start_drag)
        self.root.bind("<B1-Motion>", self._on_drag)
        self.root.bind("<ButtonRelease-1>", self._save_position)

        self._build_ui()

        # Auto-hide after timeout
        self.root.after(AUTO_HIDE_SECONDS * 1000, self.root.destroy)

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event):
        x = self.root.winfo_x() + event.x - self._drag_x
        y = self.root.winfo_y() + event.y - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    def _load_position(self) -> dict | None:
        """Load saved window position from file."""
        try:
            if POSITION_FILE.exists():
                return json.loads(POSITION_FILE.read_text())
        except (json.JSONDecodeError, KeyError):
            pass
        return None

    def _save_position(self, event=None):
        """Save current window position to file."""
        pos = {"x": self.root.winfo_x(), "y": self.root.winfo_y()}
        POSITION_FILE.parent.mkdir(parents=True, exist_ok=True)
        POSITION_FILE.write_text(json.dumps(pos))

    def _build_ui(self):
        signals = get_latest_signals()

        # Header
        now = datetime.now().strftime("%I:%M %p")
        header_text = f" 📊 GW2 Trading Signals ({now})"
        header = tk.Label(
            self.root, text=header_text, font=(FONT_FAMILY, 11, "bold"),
            bg=BG_COLOR, fg=HEADER_COLOR, anchor="w", padx=8, pady=6
        )
        header.pack(fill="x")

        # Separator
        sep = tk.Frame(self.root, height=1, bg=HEADER_COLOR)
        sep.pack(fill="x", padx=8)

        if not signals:
            no_signal = tk.Label(
                self.root, text="  No confident signals today.",
                font=(FONT_FAMILY, 10), bg=BG_COLOR, fg=TEXT_COLOR,
                anchor="w", padx=8, pady=8
            )
            no_signal.pack(fill="x")
        else:
            for signal in signals:
                line, color = format_signal_line(signal)
                label = tk.Label(
                    self.root, text=line, font=(FONT_FAMILY, 10),
                    bg=BG_COLOR, fg=color, anchor="w", padx=8, pady=2
                )
                label.pack(fill="x")

        # Dismiss button
        dismiss = tk.Label(
            self.root, text="  [click anywhere to drag • auto-closes in 60s]",
            font=(FONT_FAMILY, 8), bg=BG_COLOR, fg="#666666",
            anchor="w", padx=8, pady=6
        )
        dismiss.pack(fill="x")

    def show(self):
        self.root.mainloop()


def main():
    overlay = SignalOverlay()
    overlay.show()


if __name__ == "__main__":
    main()
