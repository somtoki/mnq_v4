"""CSV-oriented trade logging utilities for paper trading sessions."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from app.strategies.base import StrategySignal


class TradeLogger:
    """Persists paper trade, signal, and pending-order activity."""

    TRADE_FIELDNAMES = [
        "symbol",
        "side",
        "qty",
        "entry_time",
        "exit_time",
        "entry_price",
        "exit_price",
        "entry_reason",
        "exit_reason",
        "pnl_points",
        "pnl_usd",
        "mfe",
        "mae",
    ]
    SIGNAL_FIELDNAMES = [
        "timestamp",
        "symbol",
        "signal_type",
        "price",
        "reason",
        "metadata",
    ]
    PENDING_ORDER_FIELDNAMES = [
        "signal_type",
        "symbol",
        "signal_timestamp",
        "signal_price",
        "reason",
        "metadata",
    ]
    ORDER_EXECUTION_FIELDNAMES = [
        "status",
        "signal_type",
        "symbol",
        "signal_timestamp",
        "bar_timestamp",
        "bar_open",
        "execution_price",
        "reason",
        "metadata",
    ]
    POSITION_SNAPSHOT_FIELDNAMES = [
        "timestamp",
        "symbol",
        "side",
        "qty",
        "entry_time",
        "entry_price",
        "mfe",
        "mae",
        "bar_high",
        "bar_low",
        "bar_close",
    ]

    def __init__(
        self,
        trade_output_path: Path,
        signal_output_path: Path,
        pending_order_output_path: Path,
        order_execution_output_path: Path,
    ) -> None:
        """Stores the target CSV paths for runtime artifacts."""

        self._trade_output_path = trade_output_path
        self._signal_output_path = signal_output_path
        self._pending_order_output_path = pending_order_output_path
        self._order_execution_output_path = order_execution_output_path
        self._position_snapshot_output_path = (
            self._trade_output_path.parent / "position_snapshots.csv"
        )

    def initialize(self, reset: bool = False) -> None:
        """Creates CSV files with headers, optionally resetting the session."""

        self._initialize_file(self._trade_output_path, self.TRADE_FIELDNAMES, reset=reset)
        self._initialize_file(self._signal_output_path, self.SIGNAL_FIELDNAMES, reset=reset)
        self._initialize_file(
            self._pending_order_output_path,
            self.PENDING_ORDER_FIELDNAMES,
            reset=reset,
        )
        self._initialize_file(
            self._order_execution_output_path,
            self.ORDER_EXECUTION_FIELDNAMES,
            reset=reset,
        )
        self._initialize_file(
            self._position_snapshot_output_path,
            self.POSITION_SNAPSHOT_FIELDNAMES,
            reset=reset,
        )

    def log_trade(self, trade: Dict[str, Any]) -> None:
        """Appends a completed trade row to the trade CSV log."""

        self.initialize()
        normalized_row = {
            field: trade.get(field, "")
            for field in self.TRADE_FIELDNAMES
        }
        self._append_row(
            self._trade_output_path,
            self.TRADE_FIELDNAMES,
            normalized_row,
        )

    def log_position_snapshot(self, position: Dict[str, Any], bar: Dict[str, Any]) -> None:
        """Appends a snapshot of the current open position and bar state."""

        self.initialize()
        self._append_row(
            self._position_snapshot_output_path,
            self.POSITION_SNAPSHOT_FIELDNAMES,
            {
                "timestamp": bar.get("timestamp", ""),
                "symbol": position.get("symbol", ""),
                "side": position.get("side", ""),
                "qty": position.get("qty", ""),
                "entry_time": position.get("entry_time", ""),
                "entry_price": position.get("entry_price", ""),
                "mfe": position.get("mfe", ""),
                "mae": position.get("mae", ""),
                "bar_high": bar.get("high", ""),
                "bar_low": bar.get("low", ""),
                "bar_close": bar.get("close", ""),
            },
        )

    def log_signal(self, signal: StrategySignal) -> None:
        """Appends a normalized strategy signal row to the signal CSV log."""

        self.initialize()
        self._append_row(
            self._signal_output_path,
            self.SIGNAL_FIELDNAMES,
            {
                "timestamp": signal.timestamp.isoformat(),
                "symbol": signal.symbol,
                "signal_type": signal.signal_type.value,
                "price": signal.price,
                "reason": signal.reason,
                "metadata": self._serialize_metadata(signal.metadata),
            },
        )

    def log_pending_order(self, order: Dict[str, Any]) -> None:
        """Appends a queued pending-order row to the pending-order CSV log."""

        self.initialize()
        normalized_row = {
            field: order.get(field, "")
            for field in self.PENDING_ORDER_FIELDNAMES
        }
        normalized_row["metadata"] = self._serialize_metadata(order.get("metadata", {}))
        self._append_row(
            self._pending_order_output_path,
            self.PENDING_ORDER_FIELDNAMES,
            normalized_row,
        )

    def log_order_execution(
        self,
        execution: Dict[str, Any],
        bar: Dict[str, Any],
    ) -> None:
        """Appends a pending-order execution row to the execution CSV log."""

        self.initialize()
        self._append_row(
            self._order_execution_output_path,
            self.ORDER_EXECUTION_FIELDNAMES,
            {
                "status": execution.get("status", ""),
                "signal_type": execution.get("signal_type", ""),
                "symbol": execution.get("symbol", ""),
                "signal_timestamp": execution.get("signal_timestamp", ""),
                "bar_timestamp": bar.get("timestamp", ""),
                "bar_open": bar.get("open", ""),
                "execution_price": execution.get("execution_price", ""),
                "reason": execution.get("reason", ""),
                "metadata": self._serialize_metadata(execution.get("metadata", {})),
            },
        )

    def _serialize_metadata(self, metadata: Any) -> str:
        """Serializes metadata payloads consistently for CSV logs."""

        return json.dumps(metadata, ensure_ascii=True, sort_keys=True)

    def _initialize_file(
        self,
        output_path: Path,
        fieldnames: List[str],
        reset: bool = False,
    ) -> None:
        """Creates or resets a CSV file with headers."""

        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists() and not reset:
            return
        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()

    def _append_row(
        self,
        output_path: Path,
        fieldnames: List[str],
        row: Dict[str, Any],
    ) -> None:
        """Appends a row to the selected CSV file."""

        with output_path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writerow(row)
