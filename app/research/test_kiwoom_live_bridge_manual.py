"""Manual smoke test for the Kiwoom live bridge skeleton."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.broker.kiwoom_live_bridge import KiwoomLiveBridge, build_sample_kiwoom_raw_ticks


def main() -> None:
    """Runs a paper-only live bridge dry run across multiple bar boundaries."""

    bridge = KiwoomLiveBridge(symbol="MNQ", bar_minutes=15)
    bridge.start()

    completed_bars_processed = 0
    for raw_tick in build_sample_kiwoom_raw_ticks(symbol="MNQ"):
        completed_bars_processed += bridge.on_raw_tick(raw_tick)

    status = bridge.get_status()
    print("Completed bars processed: {0}".format(completed_bars_processed))
    print("Bridge status: {0}".format(status))
    bridge.stop()

    assert status["completed_bars_processed"] >= 1


if __name__ == "__main__":
    main()
