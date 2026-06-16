"""High-level coordinator for the MNQ V4 paper trading runtime."""

from __future__ import annotations

from typing import Iterable, Optional

from app.broker.base import BrokerInterface
from app.config.paper_config import PaperTradingConfig
from app.paper.execution_engine import ExecutionEngine
from app.paper.position_manager import PositionManager
from app.paper.risk_manager import RiskManager
from app.paper.signal_pipeline import SignalPipeline
from app.paper.trade_logger import TradeLogger
from app.strategies.base import StrategyInterface


class PaperTrader:
    """Coordinates strategy evaluation, execution, and logging for paper mode."""

    def __init__(
        self,
        config: PaperTradingConfig,
        broker: BrokerInterface,
        strategy: StrategyInterface,
        execution_engine: ExecutionEngine,
        position_manager: PositionManager,
        risk_manager: RiskManager,
        trade_logger: TradeLogger,
        signal_pipeline: SignalPipeline,
    ) -> None:
        """Stores runtime dependencies for the paper trading workflow."""

        self._config = config
        self._broker = broker
        self._strategy = strategy
        self._execution_engine = execution_engine
        self._position_manager = position_manager
        self._risk_manager = risk_manager
        self._trade_logger = trade_logger
        self._signal_pipeline = signal_pipeline

    def start(self) -> None:
        """Performs lightweight startup actions for paper trading mode."""

        self._strategy.reset()
        self._trade_logger.initialize(reset=True)

    def get_strategy_name(self) -> str:
        """Returns the configured strategy name for startup reporting."""

        return self._strategy.get_name()

    def get_strategy_bar_count(self) -> int:
        """Returns the current number of bars accumulated inside the strategy."""

        bars = getattr(self._strategy, "bars", [])
        return len(bars)

    def get_strategy_position_side(self) -> Optional[str]:
        """Returns the current strategy-side position state."""

        return getattr(self._strategy, "position_side", None)

    def get_pending_order_count(self) -> int:
        """Returns the current number of queued pending orders."""

        return self._execution_engine.get_pending_order_count()

    def get_realized_pnl(self) -> float:
        """Returns cumulative realized PnL for the current runtime."""

        return self._execution_engine.get_realized_pnl()

    def get_closed_trade_count(self) -> int:
        """Returns how many trades were fully closed this runtime."""

        return len(self._execution_engine.get_closed_trades())

    def get_open_position(self) -> Optional[dict]:
        """Returns the broker-side open position if one exists."""

        return self._execution_engine.get_open_position()

    def get_ignored_execution_count(self) -> int:
        """Returns how many queued executions were ignored."""

        return self._execution_engine.get_ignored_execution_count()

    def is_signal_pipeline_initialized(self) -> bool:
        """Returns whether the signal pipeline dependency is available."""

        return self._signal_pipeline is not None

    def run_bar_feed(self, bar_feed: Iterable[object], max_bars: Optional[int] = None) -> int:
        """Runs a bar feed through the signal pipeline and returns processed count."""

        processed = 0
        for bar in bar_feed:
            if max_bars is not None and processed >= max_bars:
                break
            self._signal_pipeline.process_bar(bar)
            processed += 1
        return processed

    @property
    def signal_pipeline(self) -> SignalPipeline:
        """Exposes the signal pipeline for future realtime wiring."""

        return self._signal_pipeline
