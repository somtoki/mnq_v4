"""CLI skeleton for the MNQ V4 live paper trading loop."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from app.broker.kiwoom_live_bridge import KiwoomLiveBridge, build_sample_kiwoom_raw_ticks
from app.broker.kiwoom_tick_adapter import KiwoomTickAdapter
from app.paper.live_paper_trader import LivePaperTrader
from app.realtime.live_bar_feed import LiveBarFeed
from app.research.test_kiwoom_tick_adapter_manual import build_sample_raw_ticks, run_manual_test


def parse_args() -> argparse.Namespace:
    """Parses CLI arguments for the live paper trading skeleton."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", type=str, default="MNQ", help="Symbol for live paper trading.")
    parser.add_argument("--bar-minutes", type=int, default=15, help="Bar size in minutes.")
    parser.add_argument("--dry-run-sample", action="store_true", help="Feed synthetic ticks into the live skeleton.")
    parser.add_argument(
        "--dry-run-kiwoom-adapter",
        action="store_true",
        help="Run Kiwoom tick adapter samples through the live paper trading skeleton.",
    )
    parser.add_argument(
        "--dry-run-kiwoom-bridge",
        action="store_true",
        help="Run the Kiwoom live bridge skeleton with sample raw ticks.",
    )
    return parser.parse_args()


def build_sample_ticks(symbol: str) -> List[dict]:
    """Builds synthetic ticks that create at least one completed 15-minute bar."""

    return [
        {"symbol": symbol, "timestamp": "2026-01-02T09:30:05", "price": 21000.0, "volume": 1.0},
        {"symbol": symbol, "timestamp": "2026-01-02T09:34:30", "price": 21003.0, "volume": 2.0},
        {"symbol": symbol, "timestamp": "2026-01-02T09:41:10", "price": 20998.5, "volume": 1.0},
        {"symbol": symbol, "timestamp": "2026-01-02T09:44:59", "price": 21001.5, "volume": 3.0},
        {"symbol": symbol, "timestamp": "2026-01-02T09:45:01", "price": 21004.0, "volume": 1.0},
        {"symbol": symbol, "timestamp": "2026-01-02T09:52:15", "price": 21006.5, "volume": 2.0},
    ]


def run_ticks_through_live_system(
    live_bar_feed: LiveBarFeed,
    live_trader: LivePaperTrader,
    ticks: List[dict],
) -> int:
    """Feeds normalized ticks through the live system and returns processed bar count."""

    processed_bars = 0
    for tick in ticks:
        completed_bars = live_bar_feed.ingest_tick(tick)
        for bar in completed_bars:
            live_trader.process_completed_bar(bar)
            processed_bars += 1
    for bar in live_bar_feed.flush():
        live_trader.process_completed_bar(bar)
        processed_bars += 1
    return processed_bars


def main() -> None:
    """Starts the live paper trading loop skeleton."""

    args = parse_args()
    project_root = Path(__file__).resolve().parent
    live_bar_feed = LiveBarFeed(symbol=args.symbol, bar_minutes=args.bar_minutes)
    live_trader = LivePaperTrader(
        project_root=project_root,
        symbol=args.symbol,
        bar_minutes=args.bar_minutes,
    )

    print("MNQ V4 Live Paper Trading System Started")
    print("Live bar feed initialized")

    processed_bars = 0
    if args.dry_run_sample:
        processed_bars += run_ticks_through_live_system(
            live_bar_feed=live_bar_feed,
            live_trader=live_trader,
            ticks=build_sample_ticks(args.symbol),
        )

    if args.dry_run_kiwoom_adapter:
        run_manual_test()
        adapter = KiwoomTickAdapter(symbol=args.symbol)
        normalized_ticks = [adapter.normalize(raw_tick) for raw_tick in build_sample_raw_ticks()]
        processed_bars += run_ticks_through_live_system(
            live_bar_feed=live_bar_feed,
            live_trader=live_trader,
            ticks=normalized_ticks,
        )
        print("Kiwoom tick adapter dry run completed")

    if args.dry_run_kiwoom_bridge:
        bridge = KiwoomLiveBridge(
            symbol=args.symbol,
            bar_minutes=args.bar_minutes,
        )
        bridge.start()
        bridge_processed_bars = 0
        for raw_tick in build_sample_kiwoom_raw_ticks(symbol=args.symbol):
            bridge_processed_bars += bridge.on_raw_tick(raw_tick)
        print("MNQ V4 Kiwoom Bridge Dry Run Started")
        print("Completed bars processed: {0}".format(bridge_processed_bars))
        print("Bridge status: {0}".format(bridge.get_status()))
        bridge.stop()
        processed_bars += bridge_processed_bars

    print("Completed bars processed: {0}".format(processed_bars))


if __name__ == "__main__":
    main()
