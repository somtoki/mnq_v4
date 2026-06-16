"""Adapter shell that will eventually wrap the research Turtle V4 strategy logic.

This class exists to isolate the realtime paper trading runtime from the concrete
implementation details of the future Turtle V4 port. It now emits normalized
strategy signals while still relying on the execution layer to apply the
next-bar-open fill model.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.strategies.base import SignalType, StrategyInterface, StrategySignal
from app.strategies.v4_indicator_helper import calculate_v4_indicators


class TurtleV4Adapter(StrategyInterface):
    """Placeholder adapter for the future Turtle V4 strategy port."""

    BLOCKED_ENTRY_HOURS = {15, 16, 17}
    STOP_DISTANCE_ATR = 2.0

    def __init__(
        self,
        symbol: str = "MNQ",
        max_history: int = 1000,
        donchian_entry_window: int = 30,
        donchian_exit_window: int = 10,
        atr_window: int = 20,
        trend_ma_window: int = 500,
    ) -> None:
        """Initializes history storage, position state, and indicator settings."""

        self.symbol = symbol
        self.max_history = max_history
        self.donchian_entry_window = donchian_entry_window
        self.donchian_exit_window = donchian_exit_window
        self.atr_window = atr_window
        self.trend_ma_window = trend_ma_window
        self.reset()

    def on_bar(self, bar: Any) -> StrategySignal:
        """Appends the bar, evaluates V4 conditions, and emits next-bar-open signals."""

        normalized_bar = self._append_bar(bar)
        indicators = self._calculate_indicators()
        self._update_position_tracking(normalized_bar)
        conditions = self._evaluate_conditions(normalized_bar, indicators)
        metadata = self._build_metadata(normalized_bar, indicators, conditions=conditions)

        if self._is_long() and bool(metadata.get("stop_triggered_debug")):
            return self._emit_signal(
                SignalType.LONG_EXIT,
                normalized_bar,
                "long_atr_stop",
                metadata,
            )

        if self._is_short() and bool(metadata.get("stop_triggered_debug")):
            return self._emit_signal(
                SignalType.SHORT_EXIT,
                normalized_bar,
                "short_atr_stop",
                metadata,
            )

        if self._is_long() and bool(metadata.get("opposite_exit_triggered_debug")):
            return self._emit_signal(
                SignalType.LONG_EXIT,
                normalized_bar,
                "long_exit_opposite_10",
                metadata,
            )

        if self._is_short() and bool(metadata.get("opposite_exit_triggered_debug")):
            return self._emit_signal(
                SignalType.SHORT_EXIT,
                normalized_bar,
                "short_exit_opposite_10",
                metadata,
            )

        if not self._has_position() and self.pending_signal_type is None:
            if conditions["long_entry"]:
                return self._emit_signal(
                    SignalType.LONG_ENTRY,
                    normalized_bar,
                    "long_breakout_v4",
                    metadata,
                )
            if conditions["short_entry"]:
                return self._emit_signal(
                    SignalType.SHORT_ENTRY,
                    normalized_bar,
                    "short_breakout_v4",
                    metadata,
                )

        return self._build_signal(
            SignalType.NONE,
            normalized_bar,
            "strategy_no_action",
            metadata=metadata,
        )

    def on_execution(self, execution: Dict[str, Any]) -> None:
        """Applies next-bar-open execution updates to local adapter state."""

        execution_status = str(execution.get("status", "executed"))
        signal_type = str(execution.get("signal_type", ""))
        execution_timestamp = str(execution.get("execution_timestamp", ""))
        metadata = execution.get("metadata", {})

        self.pending_signal_type = None
        self.pending_signal_reason = None

        if execution_status != "executed":
            return

        execution_price = float(execution.get("execution_price", 0.0))
        atr_at_entry = metadata.get("atr_at_entry")

        if signal_type == SignalType.LONG_ENTRY.value:
            self.position_side = "LONG"
            self.entry_price = execution_price
            self.entry_time = execution_timestamp
            self.atr_at_entry = float(atr_at_entry) if atr_at_entry is not None else None
            self.initial_stop_price = self._calculate_initial_stop_price(
                position_side=self.position_side,
                entry_price=self.entry_price,
                atr_at_entry=self.atr_at_entry,
            )
            self.highest_price_since_entry = execution_price
            self.lowest_price_since_entry = execution_price
            self.bars_since_entry = 0
            return

        if signal_type == SignalType.SHORT_ENTRY.value:
            self.position_side = "SHORT"
            self.entry_price = execution_price
            self.entry_time = execution_timestamp
            self.atr_at_entry = float(atr_at_entry) if atr_at_entry is not None else None
            self.initial_stop_price = self._calculate_initial_stop_price(
                position_side=self.position_side,
                entry_price=self.entry_price,
                atr_at_entry=self.atr_at_entry,
            )
            self.highest_price_since_entry = execution_price
            self.lowest_price_since_entry = execution_price
            self.bars_since_entry = 0
            return

        if signal_type in (SignalType.LONG_EXIT.value, SignalType.SHORT_EXIT.value):
            self.position_side = None
            self.entry_price = None
            self.entry_time = None
            self.atr_at_entry = None
            self.initial_stop_price = None
            self.highest_price_since_entry = None
            self.lowest_price_since_entry = None
            self.bars_since_entry = 0

    def get_name(self) -> str:
        """Returns the strategy adapter name."""

        return "TurtleV4Adapter"

    def reset(self) -> None:
        """Resets accumulated bars, position state, and signal state."""

        self.bars = []  # type: List[Dict[str, object]]
        self.position_side = None  # type: Optional[str]
        self.entry_price = None  # type: Optional[float]
        self.entry_time = None  # type: Optional[str]
        self.atr_at_entry = None  # type: Optional[float]
        self.initial_stop_price = None  # type: Optional[float]
        self.highest_price_since_entry = None  # type: Optional[float]
        self.lowest_price_since_entry = None  # type: Optional[float]
        self.bars_since_entry = 0
        self.last_signal_type = None  # type: Optional[str]
        self.last_signal_reason = None  # type: Optional[str]
        self.pending_signal_type = None  # type: Optional[str]
        self.pending_signal_reason = None  # type: Optional[str]

    def _append_bar(self, bar: Any) -> Dict[str, object]:
        """Validates and normalizes a new bar before storing it in history."""

        normalized_bar = self._normalize_bar(bar)
        required_fields = ["timestamp", "symbol", "open", "high", "low", "close"]
        for field in required_fields:
            if field not in normalized_bar:
                raise ValueError("Bar is missing required field: {0}".format(field))

        cleaned_bar = {
            "timestamp": str(normalized_bar["timestamp"]),
            "symbol": str(normalized_bar.get("symbol") or self.symbol),
            "open": float(normalized_bar["open"]),
            "high": float(normalized_bar["high"]),
            "low": float(normalized_bar["low"]),
            "close": float(normalized_bar["close"]),
            "volume": float(normalized_bar.get("volume", 0.0) or 0.0),
        }
        self.bars.append(cleaned_bar)
        if len(self.bars) > self.max_history:
            self.bars.pop(0)
        return cleaned_bar

    def _update_position_tracking(self, bar: Dict[str, object]) -> None:
        """Updates running position state from the latest completed bar."""

        if not self._has_position():
            return

        current_high = float(bar["high"])
        current_low = float(bar["low"])
        if self.highest_price_since_entry is None:
            self.highest_price_since_entry = current_high
        else:
            self.highest_price_since_entry = max(self.highest_price_since_entry, current_high)

        if self.lowest_price_since_entry is None:
            self.lowest_price_since_entry = current_low
        else:
            self.lowest_price_since_entry = min(self.lowest_price_since_entry, current_low)

        self.bars_since_entry += 1

    def _has_position(self) -> bool:
        """Returns whether the adapter currently tracks an open position."""

        return self.position_side is not None

    def _is_long(self) -> bool:
        """Returns whether the tracked position is long."""

        return self.position_side == "LONG"

    def _is_short(self) -> bool:
        """Returns whether the tracked position is short."""

        return self.position_side == "SHORT"

    def _check_long_entry(self, bar: Dict[str, object], indicators: Optional[Dict[str, object]]) -> bool:
        """Returns whether the current bar satisfies the V4-style long entry conditions."""

        if indicators is None:
            return False
        entry_high = indicators.get("entry_high")
        trend_ma = indicators.get("trend_ma")
        close = float(bar["close"])
        return bool(
            entry_high is not None
            and trend_ma is not None
            and close > float(entry_high)
            and close > float(trend_ma)
            and not self._has_position()
        )

    def _check_short_entry(self, bar: Dict[str, object], indicators: Optional[Dict[str, object]]) -> bool:
        """Returns whether the current bar satisfies the V4-style short entry conditions."""

        if indicators is None:
            return False
        entry_low = indicators.get("entry_low")
        trend_ma = indicators.get("trend_ma")
        close = float(bar["close"])
        return bool(
            entry_low is not None
            and trend_ma is not None
            and close < float(entry_low)
            and close < float(trend_ma)
            and not self._has_position()
        )

    def _check_long_exit(self, bar: Dict[str, object], indicators: Optional[Dict[str, object]]) -> bool:
        """Returns whether the current bar satisfies the V4-style long exit condition."""

        if indicators is None or not self._is_long():
            return False
        exit_low = indicators.get("exit_low")
        close = float(bar["close"])
        return exit_low is not None and close < float(exit_low)

    def _check_short_exit(self, bar: Dict[str, object], indicators: Optional[Dict[str, object]]) -> bool:
        """Returns whether the current bar satisfies the V4-style short exit condition."""

        if indicators is None or not self._is_short():
            return False
        exit_high = indicators.get("exit_high")
        close = float(bar["close"])
        return exit_high is not None and close > float(exit_high)

    def _evaluate_conditions(
        self,
        bar: Dict[str, object],
        indicators: Optional[Dict[str, object]],
    ) -> Dict[str, bool]:
        """Evaluates debug-only V4 entry and exit conditions for the current bar."""

        conditions = self._base_condition_flags(bar, indicators)
        conditions["long_entry"] = bool(
            conditions["raw_long_breakout"]
            and conditions["long_trend_filter_pass"]
            and not self._has_position()
            and self.pending_signal_type is None
        )
        conditions["short_entry"] = bool(
            conditions["raw_short_breakout"]
            and conditions["short_trend_filter_pass"]
            and not self._has_position()
            and self.pending_signal_type is None
        )
        conditions["long_exit"] = self._check_long_exit(bar, indicators)
        conditions["short_exit"] = self._check_short_exit(bar, indicators)
        return conditions

    def _base_condition_flags(
        self,
        bar: Dict[str, object],
        indicators: Optional[Dict[str, object]],
    ) -> Dict[str, bool]:
        """Builds the non-ordering debug flags that mirror legacy V4 filtering."""

        close = float(bar["close"])
        raw_long_breakout = False
        raw_short_breakout = False
        long_trend_filter_pass = False
        short_trend_filter_pass = False
        long_channel_width_exception = False

        if indicators is not None:
            entry_high = indicators.get("entry_high")
            entry_low = indicators.get("entry_low")
            raw_long_breakout = (
                entry_high is not None and close > float(entry_high) and not self._has_position()
            )
            raw_short_breakout = (
                entry_low is not None and close < float(entry_low) and not self._has_position()
            )

            channel_width_atr = indicators.get("channel_width_atr")
            trend_ma = indicators.get("trend_ma")
            trend_ma_previous = indicators.get("trend_ma_previous")
            trend_ma_slope_up = bool(indicators.get("trend_ma_slope_up"))
            trend_ma_slope_down = bool(indicators.get("trend_ma_slope_down"))

            if channel_width_atr is not None:
                if float(channel_width_atr) <= 3.0:
                    long_trend_filter_pass = True
                    long_channel_width_exception = True
                elif float(channel_width_atr) < 5.0:
                    if trend_ma is not None and trend_ma_previous is not None:
                        ma500_slope = float(trend_ma) - float(trend_ma_previous)
                        long_trend_filter_pass = ma500_slope >= -0.5
                    long_channel_width_exception = True
                else:
                    long_trend_filter_pass = trend_ma_slope_up
            else:
                long_trend_filter_pass = trend_ma_slope_up

            short_trend_filter_pass = trend_ma_slope_down

        return {
            "raw_long_breakout": raw_long_breakout,
            "raw_short_breakout": raw_short_breakout,
            "long_trend_filter_pass": long_trend_filter_pass,
            "short_trend_filter_pass": short_trend_filter_pass,
            "long_channel_width_exception": long_channel_width_exception,
            "blocked_by_entry_hour": False,
        }

    def _is_blocked_entry_hour(self, bar: Dict[str, object]) -> bool:
        """Returns a debug-only current-bar blocked-hour flag."""

        hour = datetime.fromisoformat(str(bar["timestamp"])).hour
        return hour in self.BLOCKED_ENTRY_HOURS

    def _calculate_initial_stop_price(
        self,
        position_side: Optional[str],
        entry_price: Optional[float],
        atr_at_entry: Optional[float],
    ) -> Optional[float]:
        """Returns the legacy fixed 2 ATR initial stop for the active position."""

        if position_side is None or entry_price is None or atr_at_entry is None:
            return None
        stop_offset = self.STOP_DISTANCE_ATR * atr_at_entry
        if position_side == "LONG":
            return entry_price - stop_offset
        if position_side == "SHORT":
            return entry_price + stop_offset
        return None

    def _build_exit_debug(
        self,
        bar: Dict[str, object],
        conditions: Optional[Dict[str, bool]],
    ) -> Dict[str, object]:
        """Builds legacy stop/opposite-exit debug fields without emitting stop orders yet."""

        opposite_exit_triggered = False
        if conditions is not None:
            opposite_exit_triggered = bool(
                conditions.get("long_exit") or conditions.get("short_exit")
            )

        stop_triggered = False
        if self._has_position() and self.initial_stop_price is not None:
            stop_price = float(self.initial_stop_price)
            if self._is_long():
                stop_triggered = float(bar["low"]) <= stop_price
            elif self._is_short():
                stop_triggered = float(bar["high"]) >= stop_price

        if stop_triggered and opposite_exit_triggered:
            exit_priority_debug = "atr_stop_over_opposite_10"
        elif stop_triggered:
            exit_priority_debug = "atr_stop_only"
        elif opposite_exit_triggered:
            exit_priority_debug = "opposite_10_only"
        else:
            exit_priority_debug = "none"

        return {
            "stop_triggered_debug": stop_triggered,
            "opposite_exit_triggered_debug": opposite_exit_triggered,
            "exit_priority_debug": exit_priority_debug,
        }

    def _emit_signal(
        self,
        signal_type: SignalType,
        bar: Dict[str, object],
        reason: str,
        metadata: Dict[str, object],
    ) -> StrategySignal:
        """Stores signal state for queued execution and returns a normalized signal."""

        self.last_signal_type = signal_type.value
        self.last_signal_reason = reason
        self.pending_signal_type = signal_type.value
        self.pending_signal_reason = reason
        metadata = dict(metadata)
        metadata["last_signal_type"] = self.last_signal_type
        metadata["last_signal_reason"] = self.last_signal_reason
        metadata["pending_signal_type"] = self.pending_signal_type
        metadata["pending_signal_reason"] = self.pending_signal_reason
        return self._build_signal(signal_type, bar, reason, metadata=metadata)

    def _build_signal(
        self,
        signal_type: SignalType,
        bar: Dict[str, object],
        reason: str,
        metadata: Optional[Dict[str, object]] = None,
    ) -> StrategySignal:
        """Builds a normalized strategy signal."""

        return StrategySignal(
            signal_type=signal_type,
            symbol=str(bar["symbol"]),
            timestamp=datetime.fromisoformat(str(bar["timestamp"])),
            price=float(bar["close"]),
            reason=reason,
            metadata=metadata or {},
        )

    def _build_metadata(
        self,
        bar: Dict[str, object],
        indicators: Optional[Dict[str, object]],
        conditions: Optional[Dict[str, bool]] = None,
    ) -> Dict[str, object]:
        """Builds a consistent metadata payload for outgoing strategy signals."""

        atr_value = None
        if self.atr_at_entry is not None:
            atr_value = self.atr_at_entry
        elif indicators is not None and indicators.get("atr") is not None:
            atr_value = float(indicators["atr"])

        metadata = {
            "history_length": len(self.bars),
            "indicator_ready": self._is_ready(indicators),
            "indicators": indicators,
            "conditions": conditions,
            "position_side": self.position_side,
            "entry_price": self.entry_price,
            "entry_time": self.entry_time,
            "atr_at_entry": atr_value,
            "initial_stop_price": self.initial_stop_price,
            "stop_distance_atr": self.STOP_DISTANCE_ATR,
            "highest_price_since_entry": self.highest_price_since_entry,
            "lowest_price_since_entry": self.lowest_price_since_entry,
            "bars_since_entry": self.bars_since_entry,
            "last_signal_type": self.last_signal_type,
            "last_signal_reason": self.last_signal_reason,
            "pending_signal_type": self.pending_signal_type,
            "pending_signal_reason": self.pending_signal_reason,
            "entry_block_hour_basis": "next_bar_hour_pending_execution_layer",
        }
        metadata.update(self._build_exit_debug(bar, conditions))
        return metadata

    def _is_ready(self, indicators: Optional[Dict[str, object]] = None) -> bool:
        """Returns whether helper-calculated indicators are ready for V4 checks."""

        if indicators is None:
            indicators = self._calculate_indicators()
        return bool(indicators.get("ready")) if indicators is not None else False

    def _calculate_indicators(self) -> Dict[str, object]:
        """Calculates indicator inputs through the shared V4 helper module."""

        return calculate_v4_indicators(
            self.bars,
            entry_window=self.donchian_entry_window,
            exit_window=self.donchian_exit_window,
            atr_window=self.atr_window,
            trend_ma_window=self.trend_ma_window,
        )

    def _normalize_bar(self, bar: Any) -> Dict[str, object]:
        """Normalizes dict-like or object-like input into a common bar dictionary."""

        if isinstance(bar, dict):
            return bar
        return {
            "symbol": getattr(bar, "symbol", self.symbol),
            "timestamp": getattr(bar, "end_time").isoformat(),
            "open": getattr(bar, "open"),
            "high": getattr(bar, "high"),
            "low": getattr(bar, "low"),
            "close": getattr(bar, "close"),
            "volume": getattr(bar, "volume", 0.0),
        }
