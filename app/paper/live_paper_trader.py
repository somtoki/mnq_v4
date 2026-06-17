"""Real-time paper trading loop skeleton for completed bar processing."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from app.config.paper_config import PaperTradingConfig
from app.paper.execution_engine import ExecutionEngine
from app.paper.paper_broker import PaperBroker
from app.paper.signal_pipeline import SignalPipeline
from app.paper.trade_logger import TradeLogger
from app.strategies.turtle_v4_adapter import TurtleV4Adapter


class LivePaperTrader:
    """Processes completed realtime bars through the paper trading pipeline."""

    def __init__(
        self,
        project_root: Path,
        symbol: str = "MNQ",
        bar_minutes: int = 15,
    ) -> None:
        """Initializes strategy, broker, execution engine, and logging."""

        self._config = PaperTradingConfig(project_root=project_root)
        self._config.symbol = symbol
        self._config.timeframe_minutes = bar_minutes
        self._broker = PaperBroker(starting_balance=self._config.starting_balance)
        self._trade_logger = TradeLogger(
            trade_output_path=self._config.paper_data_dir / "trades.csv",
            signal_output_path=self._config.paper_data_dir / "signals.csv",
            pending_order_output_path=self._config.paper_data_dir / "pending_orders.csv",
            order_execution_output_path=self._config.paper_data_dir / "order_executions.csv",
        )
        self._execution_engine = ExecutionEngine(
            broker=self._broker,
            trade_logger=self._trade_logger,
        )
        self._strategy = TurtleV4Adapter(symbol=symbol)
        self._signal_pipeline = SignalPipeline(
            strategy=self._strategy,
            execution_engine=self._execution_engine,
            trade_logger=self._trade_logger,
        )
        self._processed_bar_count = 0
        self._strategy.reset()
        self._trade_logger.initialize(reset=True)

    def process_completed_bar(self, bar: Dict[str, object]) -> None:
        """Routes one completed bar through the signal pipeline and prints status."""

        self._signal_pipeline.process_bar(bar)
        self._processed_bar_count += 1
        open_position = self._execution_engine.get_open_position()
        position_side = open_position["side"] if open_position is not None else None
        print(
            "{0} close={1} position={2} realized_pnl={3} pending_orders={4}".format(
                bar.get("timestamp", ""),
                bar.get("close", ""),
                position_side,
                self._execution_engine.get_realized_pnl(),
                self._execution_engine.get_pending_order_count(),
            )
        )

    def get_processed_bar_count(self) -> int:
        """Returns how many completed bars were processed."""

        return self._processed_bar_count

    def get_open_position(self) -> Optional[Dict[str, object]]:
        """Returns the active paper position, if one exists."""

        return self._execution_engine.get_open_position()

    def get_realized_pnl(self) -> float:
        """Returns cumulative realized paper PnL."""

        return self._execution_engine.get_realized_pnl()

    def get_pending_orders(self) -> List[Dict[str, object]]:
        """Returns a copy of queued paper orders waiting for next-bar execution."""

        return [dict(order) for order in self._execution_engine.pending_orders]
