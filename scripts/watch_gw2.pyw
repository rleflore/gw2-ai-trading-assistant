"""GW2 process watcher — detects Guild Wars 2 launch and shows signal overlay.

Run this script at Windows startup (e.g., via Task Scheduler or Startup folder).
It polls for the GW2 process every 30 seconds. When detected, shows the overlay once.
After the game closes, resets and watches again for the next session.

Use .pyw extension (or pythonw.exe) to run without a console window.
"""

import subprocess
import sys
import time
from pathlib import Path

POLL_INTERVAL = 30  # seconds between checks
GW2_PROCESS_NAME = "Gw2-64.exe"


def is_gw2_running() -> bool:
    """Check if Guild Wars 2 is currently running."""
    try:
        output = subprocess.check_output(
            ["tasklist", "/FI", f"IMAGENAME eq {GW2_PROCESS_NAME}"],
            text=True, creationflags=subprocess.CREATE_NO_WINDOW
        )
        return GW2_PROCESS_NAME.lower() in output.lower()
    except subprocess.CalledProcessError:
        return False


def show_overlay():
    """Launch the signal overlay script."""
    overlay_script = Path(__file__).parent / "signal_overlay.py"
    python_exe = Path(__file__).resolve().parent.parent / "venv" / "Scripts" / "pythonw.exe"

    if not python_exe.exists():
        python_exe = sys.executable

    subprocess.Popen([str(python_exe), str(overlay_script)])


def main():
    """Watch for GW2 and show overlay on launch."""
    print(f"Watching for {GW2_PROCESS_NAME}... (polling every {POLL_INTERVAL}s)")
    shown_this_session = False

    while True:
        if is_gw2_running():
            if not shown_this_session:
                print("GW2 detected! Showing signal overlay...")
                time.sleep(10)  # Wait for game to finish loading
                show_overlay()
                shown_this_session = True
        else:
            if shown_this_session:
                print("GW2 closed. Watching for next session...")
                shown_this_session = False

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
