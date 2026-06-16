"""Bar aggregation utilities for transforming ticks into timeframe candles."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class PriceTick:
    """Represents a normalized realtime price update."""

    symbol: str
    price: float
    timestamp: datetime
    volume: float = 0.0


@dataclass
class Bar:
    """Represents a completed or in-progress OHLCV bar."""

    symbol: str
    start_time: datetime
    end_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class BarBuilder:
    """Builds fixed-timeframe bars from normalized tick inputs."""

    def __init__(self, timeframe_minutes: int) -> None:
        """Stores the target timeframe for aggregation."""

        self._timeframe_minutes = timeframe_minutes
        self._current_bar = None  # type: Optional[Bar]

    def update(self, tick: PriceTick) -> Optional[Bar]:
        """Consumes a tick and returns a completed bar when available."""

        bucket_start = self._floor_timestamp(tick.timestamp)
        bucket_end = bucket_start + timedelta(minutes=self._timeframe_minutes)

        if self._current_bar is None:
            self._current_bar = Bar(
                symbol=tick.symbol,
                start_time=bucket_start,
                end_time=bucket_end,
                open=tick.price,
                high=tick.price,
                low=tick.price,
                close=tick.price,
                volume=tick.volume,
            )
            return None

        if bucket_start == self._current_bar.start_time:
            self._current_bar.high = max(self._current_bar.high, tick.price)
            self._current_bar.low = min(self._current_bar.low, tick.price)
            self._current_bar.close = tick.price
            self._current_bar.volume += tick.volume
            return None

        completed_bar = self._current_bar
        self._current_bar = Bar(
            symbol=tick.symbol,
            start_time=bucket_start,
            end_time=bucket_end,
            open=tick.price,
            high=tick.price,
            low=tick.price,
            close=tick.price,
            volume=tick.volume,
        )
        return completed_bar

    def flush(self) -> Optional[Bar]:
        """Returns the current in-progress bar and clears local state."""

        if self._current_bar is None:
            return None
        completed_bar = self._current_bar
        self._current_bar = None
        return completed_bar

    def _floor_timestamp(self, timestamp: datetime) -> datetime:
        """Floors a timestamp down to the configured timeframe boundary."""

        floored_minute = (timestamp.minute // self._timeframe_minutes) * self._timeframe_minutes
        return timestamp.replace(minute=floored_minute, second=0, microsecond=0)
