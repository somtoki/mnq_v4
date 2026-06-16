"""Entry point for starting the MNQ V4 paper trading runtime skeleton."""

from __future__ import annotations

import argparse
from datetime import time
from pathlib import Path

from app.config.paper_config import PaperTradingConfig
from app.paper.execution_engine import ExecutionEngine
from app.paper.paper_broker import PaperBroker
from app.paper.paper_trader import PaperTrader
from app.paper.position_manager import PositionManager
from app.paper.risk_manager import RiskManager
from app.paper.signal_pipeline import SignalPipeline
from app.paper.trade_logger import TradeLogger
from app.realtime.market_clock import MarketClock, SessionWindow
from app.research.csv_bar_feed import CsvBarFeed
from app.research.report_paper_performance import generate_report
from app.strategies.turtle_v4_adapter import TurtleV4Adapter


def build_paper_trader(project_root: Path) -> PaperTrader:
    """Builds the paper trading runtime dependencies for local execution."""

    config = PaperTradingConfig(project_root=project_root)
    broker = PaperBroker(starting_balance=config.starting_balance)
    position_manager = PositionManager()
    risk_manager = RiskManager(config=config, position_manager=position_manager)
    trade_logger = TradeLogger(
        trade_output_path=config.paper_data_dir / "trades.csv",
        signal_output_path=config.paper_data_dir / "signals.csv",
        pending_order_output_path=config.paper_data_dir / "pending_orders.csv",
        order_execution_output_path=config.paper_data_dir / "order_executions.csv",
    )
    execution_engine = ExecutionEngine(broker=broker, trade_logger=trade_logger)
    strategy = TurtleV4Adapter()
    signal_pipeline = SignalPipeline(
        strategy=strategy,
        execution_engine=execution_engine,
        trade_logger=trade_logger,
    )

    _ = MarketClock(
        regular_session=SessionWindow(
            start=time(hour=0, minute=0),
            end=time(hour=23, minute=59),
        )
    )

    return PaperTrader(
        config=config,
        broker=broker,
        strategy=strategy,
        execution_engine=execution_engine,
        position_manager=position_manager,
        risk_manager=risk_manager,
        trade_logger=trade_logger,
        signal_pipeline=signal_pipeline,
    )


def parse_args() -> argparse.Namespace:
    """Parses command-line arguments for startup and CSV replay."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=str, default="", help="CSV file path for bar replay.")
    parser.add_argument("--symbol", type=str, default="MNQ", help="Symbol name for replayed bars.")
    parser.add_argument("--max-bars", type=int, default=None, help="Maximum number of bars to process.")
    parser.add_argument("--report", action="store_true", help="Generate performance report after CSV replay.")
    return parser.parse_args()


def main() -> None:
    """Starts the paper trading runtime skeleton."""

    args = parse_args()
    project_root = Path(__file__).resolve().parent
    trader = build_paper_trader(project_root)
    trader.start()
    print("MNQ V4 Paper Trading System Started")
    print("Strategy: {0}".format(trader.get_strategy_name()))
    print("Signal pipeline initialized")

    if args.csv:
        csv_path = Path(args.csv)
        bar_feed = CsvBarFeed(csv_path=str(csv_path), symbol=args.symbol)
        processed = trader.run_bar_feed(bar_feed, max_bars=args.max_bars)
        open_position = trader.get_open_position()
        final_position = open_position["side"] if open_position is not None else None
        print("CSV bar feed started: {0}".format(args.csv))
        print("Bars processed: {0}".format(processed))
        print("Strategy bars loaded: {0}".format(trader.get_strategy_bar_count()))
        print("Closed trades: {0}".format(trader.get_closed_trade_count()))
        print("Realized PnL USD: {0}".format(trader.get_realized_pnl()))
        print("Final position: {0}".format(final_position))
        print("Pending orders left: {0}".format(trader.get_pending_order_count()))
        if args.report:
            report_dir = project_root / "reports" / "paper_performance"
            trades_path = project_root / "data" / "paper" / "trades.csv"
            report_summary = generate_report(trades_path=trades_path, output_dir=report_dir)
            print("Win rate: {0}".format(report_summary["win_rate"]))
            print("Profit factor: {0}".format(report_summary["profit_factor"]))
            print("Max drawdown USD: {0}".format(report_summary["max_drawdown_usd"]))
            print("Report path: {0}".format(report_summary["report_path"]))


if __name__ == "__main__":
    main()
