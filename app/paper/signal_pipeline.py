"""Routes completed bars through strategy evaluation and execution."""

from __future__ import annotations

from typing import Any, Dict, List

from app.paper.execution_engine import ExecutionEngine
from app.paper.trade_logger import TradeLogger
from app.strategies.base import SignalType, StrategyInterface, StrategySignal


class SignalPipeline:
    """Connects completed bars to strategy evaluation and next-bar-open execution."""

    def __init__(
        self,
        strategy: StrategyInterface,
        execution_engine: ExecutionEngine,
        trade_logger: TradeLogger,
    ) -> None:
        """Stores the strategy, execution engine, and logger dependencies."""

        self._strategy = strategy
        self._execution_engine = execution_engine
        self._trade_logger = trade_logger

    def process_bar(self, bar: object) -> StrategySignal:
        """Processes pending orders at bar open, then evaluates the current bar."""

        normalized_bar = self._normalize_bar(bar)
        executions = self._execution_engine.process_pending_orders_at_bar_open(normalized_bar)
        self._dispatch_executions(executions)
        self._execution_engine.update_open_position_from_bar(normalized_bar)
        signal = self._strategy.on_bar(normalized_bar)
        return self.handle_signal(signal)

    def handle_signal(self, signal: StrategySignal) -> StrategySignal:
        """Logs the signal and queues it when it is actionable."""

        self._trade_logger.log_signal(signal)
        if signal.signal_type == SignalType.NONE:
            return signal
        self._execution_engine.queue_signal(signal)
        return signal

    def _dispatch_executions(self, executions: List[Dict[str, Any]]) -> None:
        """Notifies the strategy when queued signals are executed."""

        if not executions:
            return
        callback = getattr(self._strategy, "on_execution", None)
        if callback is None or not callable(callback):
            return
        for execution in executions:
            callback(execution)

    def _normalize_bar(self, bar: Any) -> Dict[str, Any]:
        """Normalizes dict-like or object-like bar input for queue processing."""

        if isinstance(bar, dict):
            return bar
        return {
            "symbol": getattr(bar, "symbol"),
            "timestamp": getattr(bar, "end_time").isoformat(),
            "open": getattr(bar, "open"),
            "high": getattr(bar, "high"),
            "low": getattr(bar, "low"),
            "close": getattr(bar, "close"),
            "volume": getattr(bar, "volume", 0.0),
        }
