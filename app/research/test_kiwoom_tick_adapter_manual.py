"""Manual sanity checks for the Kiwoom tick normalization adapter."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.broker.kiwoom_tick_adapter import KiwoomTickAdapter


def build_sample_raw_ticks() -> List[Dict[str, object]]:
    """Builds sample raw ticks that resemble future Kiwoom realtime payloads."""

    return [
        {
            "symbol": "MNQ",
            "datetime": "2026-01-02T09:30:05",
            "current_price": "21000.25",
            "volume": "1",
        },
        {
            "종목코드": "MNQ",
            "date": "20260102",
            "time": "094459",
            "현재가": "+21001.75",
            "거래량": "3",
        },
        {
            "code": "MNQ",
            "date": "20260102",
            "체결시간": "094501",
            "close": "21004.00",
            "qty": 2,
        },
        {
            "symbol_code": "MNQ",
            "timestamp": "20260102095215",
            "price": "21006.50",
            "contract_volume": "4",
        },
    ]


def run_manual_test() -> List[Dict[str, object]]:
    """Normalizes sample ticks, prints them, and validates key fields."""

    adapter = KiwoomTickAdapter(symbol="MNQ")
    normalized_ticks: List[Dict[str, object]] = []
    for raw_tick in build_sample_raw_ticks():
        normalized_tick = adapter.normalize(raw_tick)
        normalized_ticks.append(normalized_tick)
        print(normalized_tick)
        assert normalized_tick["symbol"] == "MNQ"
        assert isinstance(normalized_tick["price"], float)
        assert "volume" in normalized_tick
    return normalized_ticks


def main() -> None:
    """Runs the manual adapter smoke test."""

    run_manual_test()


if __name__ == "__main__":
    main()
