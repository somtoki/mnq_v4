"""Live bar feed skeleton that converts incoming ticks into completed bars."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from app.realtime.bar_builder import Bar, BarBuilder, PriceTick


class LiveBarFeed:
    """Accepts incoming ticks and emits completed bars when available."""

    def __init__(self, symbol: str = "MNQ", bar_minutes: int = 15) -> None:
        """Initializes the feed with a target symbol and bar builder."""

        self._symbol = symbol
        self._bar_builder = BarBuilder(timeframe_minutes=bar_minutes)

    def ingest_tick(self, tick: Dict[str, object]) -> List[Dict[str, object]]:
        """Consumes one tick dict and returns zero or more completed bars."""

        normalized_tick = self._normalize_tick(tick)
        completed_bar = self._bar_builder.update(normalized_tick)
        if completed_bar is None:
            return []
        return [self._bar_to_dict(completed_bar)]

    def flush(self) -> List[Dict[str, object]]:
        """Returns the current in-progress bar as a completed bar for dry runs."""

        completed_bar = self._bar_builder.flush()
        if completed_bar is None:
            return []
        return [self._bar_to_dict(completed_bar)]

    def _normalize_tick(self, tick: Dict[str, object]) -> PriceTick:
        """Normalizes a future realtime tick payload into PriceTick."""

        timestamp_value = tick.get("timestamp")
        if isinstance(timestamp_value, datetime):
            timestamp = timestamp_value
        else:
            timestamp = datetime.fromisoformat(str(timestamp_value))
        return PriceTick(
            symbol=str(tick.get("symbol", self._symbol)),
            price=float(tick["price"]),
            timestamp=timestamp,
            volume=float(tick.get("volume", 0.0) or 0.0),
        )

    def _bar_to_dict(self, bar: Bar) -> Dict[str, object]:
        """Converts a completed Bar dataclass into the strategy bar format."""

        return {
            "symbol": bar.symbol,
            "timestamp": bar.end_time.isoformat(),
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
        }
