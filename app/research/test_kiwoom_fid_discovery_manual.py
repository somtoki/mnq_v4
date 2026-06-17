"""Manual smoke test for Kiwoom realtime FID discovery logging."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.broker.kiwoom_live_bridge import KiwoomLiveBridge
from app.broker.kiwoom_openapi_client import KiwoomOpenApiClient, build_sample_fid_payloads


def run_manual_discovery() -> Path:
    """Runs a fake FID discovery flow and returns the created CSV path."""

    bridge = KiwoomLiveBridge(symbol="MNQ", bar_minutes=15)
    client = KiwoomOpenApiClient(bridge=bridge, symbol="MNQ")
    log_path = PROJECT_ROOT / "data" / "live" / "test_kiwoom_fid_discovery.csv"
    if log_path.exists():
        log_path.unlink()

    bridge.start()
    client.enable_discovery_mode(fid_log_path=str(log_path))

    for fid_values in build_sample_fid_payloads(symbol="MNQ"):
        extracted = client.extract_candidate_fids(
            code="MNQ",
            real_type="OVERSEAS_FUTURES_TICK",
            fid_values=fid_values,
        )
        client.log_fid_snapshot(
            code="MNQ",
            real_type="OVERSEAS_FUTURES_TICK",
            fid_values=extracted,
        )
        raw_tick = client.build_raw_tick_from_fids(code="MNQ", fid_values=extracted)
        bridge.on_raw_tick(raw_tick)

    bridge.stop()
    assert log_path.exists()
    return log_path


def main() -> None:
    """Executes the discovery smoke test and prints the first few CSV rows."""

    log_path = run_manual_discovery()
    print("FID log path: {0}".format(log_path))

    with log_path.open("r", newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))

    preview_rows = rows[:4]
    for row in preview_rows:
        print(row)


if __name__ == "__main__":
    main()
