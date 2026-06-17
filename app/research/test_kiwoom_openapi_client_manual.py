"""Manual smoke test for the optional Kiwoom OpenAPI client skeleton."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.broker.kiwoom_live_bridge import KiwoomLiveBridge
from app.broker.kiwoom_openapi_client import KiwoomOpenApiClient, build_sample_fid_payloads


def main() -> None:
    """Builds sample raw ticks from fake FIDs and feeds them into the bridge."""

    bridge = KiwoomLiveBridge(symbol="MNQ", bar_minutes=15)
    client = KiwoomOpenApiClient(bridge=bridge, symbol="MNQ")

    bridge.start()
    print("Kiwoom OpenAPI available: {0}".format(client.is_available()))

    completed_bars_processed = 0
    for fid_values in build_sample_fid_payloads(symbol="MNQ"):
        raw_tick = client.build_raw_tick_from_fids(code="MNQ", fid_values=fid_values)
        print("Raw tick from FIDs: {0}".format(raw_tick))
        completed_bars_processed += bridge.on_raw_tick(raw_tick)

    print("Completed bars processed: {0}".format(completed_bars_processed))
    print("Bridge status: {0}".format(bridge.get_status()))
    bridge.stop()


if __name__ == "__main__":
    main()
