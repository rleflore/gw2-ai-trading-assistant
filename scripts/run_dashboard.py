"""Entry point for the Streamlit dashboard.

Usage:
    python scripts/run_dashboard.py
"""

import subprocess
import sys
from pathlib import Path

APP_PATH = Path(__file__).resolve().parent.parent / "src" / "gw2trading" / "dashboard" / "app.py"

if __name__ == "__main__":
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(APP_PATH), "--server.headless=true"])
