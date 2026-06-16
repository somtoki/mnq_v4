"""Paper broker implementation used by the MNQ V4 simulation runtime."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.broker.base import BrokerInterface, BrokerPosition, OrderRequest, OrderResult


class PaperBroker(BrokerInterface):
    """Implements broker-like paper fills plus trade lifecycle tracking."""

    def __init__(self, starting_balance: float, point_value_usd: float = 2.0) -> None:
        """Initializes broker state for paper trading."""

        self._balance = starting_balance
        self._point_value_usd = point_value_usd
        self._positions: Dict[str, BrokerPosition] = {}
        self._order_sequence = 0
        self._open_position = None  # type: Optional[Dict[str, Any]]
        self._closed_trades = []  # type: List[Dict[str, Any]]
        self._realized_pnl = 0.0

    def buy(self, request: OrderRequest) -> OrderResult:
        """Registers a placeholder buy order result for future expansion."""

        return self._submit_order(request)

    def sell(self, request: OrderRequest) -> OrderResult:
        """Registers a placeholder sell order result for future expansion."""

        return self._submit_order(request)

    def close_position(self, symbol: object) -> Optional[object]:
        """Closes a stored paper position if one exists."""

        if isinstance(symbol, str):
            position = self._positions.pop(symbol, None)
            if position is None:
                return None
            self._open_position = None
            side = "sell" if position.side == "long" else "buy"
            request = OrderRequest(
                symbol=position.symbol,
                side=side,
                quantity=position.quantity,
                strategy_tag="paper_close",
            )
            return self._submit_order(request)

        return self._close_position_from_execution(symbol)

    def get_balance(self) -> float:
        """Returns the configured paper account balance snapshot."""

        return self._balance

    def get_positions(self) -> List[BrokerPosition]:
        """Returns all currently tracked paper positions."""

        return list(self._positions.values())

    def open_position(self, execution: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Creates an open position from an executed entry if none is active."""

        if self._open_position is not None:
            return None

        signal_type = str(execution.get("signal_type", ""))
        if signal_type not in {"LONG_ENTRY", "SHORT_ENTRY"}:
            return None

        side = "long" if signal_type == "LONG_ENTRY" else "short"
        qty = int(execution.get("qty", 1) or 1)
        position = {
            "symbol": str(execution.get("symbol", "")),
            "side": side,
            "qty": qty,
            "entry_time": str(execution.get("execution_timestamp", "")),
            "entry_price": float(execution.get("execution_price", 0.0)),
            "entry_reason": str(execution.get("reason", "")),
            "entry_signal_timestamp": str(execution.get("signal_timestamp", "")),
            "entry_metadata": dict(execution.get("metadata", {})),
            "mfe": 0.0,
            "mae": 0.0,
        }
        self._open_position = position
        self._positions[position["symbol"]] = BrokerPosition(
            symbol=str(position["symbol"]),
            quantity=qty,
            side=side,
            average_price=float(position["entry_price"]),
            opened_at=datetime.fromisoformat(str(position["entry_time"])),
        )
        return dict(position)

    def get_open_position(self) -> Optional[Dict[str, Any]]:
        """Returns the currently open paper position if one exists."""

        if self._open_position is None:
            return None
        return dict(self._open_position)

    def get_closed_trades(self) -> List[Dict[str, Any]]:
        """Returns every completed closed trade for the current runtime."""

        return [dict(trade) for trade in self._closed_trades]

    def get_realized_pnl(self) -> float:
        """Returns cumulative realized PnL in USD."""

        return self._realized_pnl

    def update_open_position_from_bar(self, bar: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Updates MFE and MAE for the active open position using the current bar."""

        if self._open_position is None:
            return None

        position = self._open_position
        entry_price = float(position["entry_price"])
        bar_high = float(bar.get("high", entry_price))
        bar_low = float(bar.get("low", entry_price))
        if str(position["side"]) == "long":
            favorable_points = max(bar_high - entry_price, 0.0)
            adverse_points = max(entry_price - bar_low, 0.0)
        else:
            favorable_points = max(entry_price - bar_low, 0.0)
            adverse_points = max(bar_high - entry_price, 0.0)

        position["mfe"] = max(float(position["mfe"]), favorable_points)
        position["mae"] = max(float(position["mae"]), adverse_points)
        return dict(position)

    def _close_position_from_execution(
        self,
        execution: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Closes the current position from an executed exit when sides line up."""

        if self._open_position is None:
            return None

        signal_type = str(execution.get("signal_type", ""))
        expected_signal_type = (
            "LONG_EXIT" if str(self._open_position["side"]) == "long" else "SHORT_EXIT"
        )
        if signal_type != expected_signal_type:
            return None

        position = self._open_position
        exit_price = float(execution.get("execution_price", 0.0))
        qty = int(position["qty"])
        if str(position["side"]) == "long":
            pnl_points = exit_price - float(position["entry_price"])
        else:
            pnl_points = float(position["entry_price"]) - exit_price
        pnl_usd = pnl_points * self._point_value_usd * qty

        trade = {
            "symbol": str(position["symbol"]),
            "side": str(position["side"]),
            "qty": qty,
            "entry_time": str(position["entry_time"]),
            "exit_time": str(execution.get("execution_timestamp", "")),
            "entry_price": float(position["entry_price"]),
            "exit_price": exit_price,
            "entry_reason": str(position["entry_reason"]),
            "exit_reason": str(execution.get("reason", "")),
            "pnl_points": pnl_points,
            "pnl_usd": pnl_usd,
            "mfe": float(position["mfe"]),
            "mae": float(position["mae"]),
            "exit_signal_timestamp": str(execution.get("signal_timestamp", "")),
            "exit_metadata": dict(execution.get("metadata", {})),
        }
        self._closed_trades.append(trade)
        self._realized_pnl += pnl_usd
        self._positions.pop(str(position["symbol"]), None)
        self._open_position = None
        return dict(trade)

    def _submit_order(self, request: OrderRequest) -> OrderResult:
        """Builds a normalized order result without real execution routing."""

        self._order_sequence += 1
        return OrderResult(
            order_id="PAPER-{0}".format(self._order_sequence),
            symbol=request.symbol,
            side=request.side,
            quantity=request.quantity,
            filled_price=request.price,
            status="accepted",
            timestamp=datetime.now(),
            metadata={"order_type": request.order_type},
        )
