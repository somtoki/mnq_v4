"""Standard-library indicator helpers for the legacy Turtle V4 migration."""

from __future__ import annotations

from typing import Dict, List, Optional


def safe_float(value, default=None):
    """Convert a value to float when possible and return the default otherwise."""

    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _previous_window_values(
    bars: List[Dict[str, object]],
    window: int,
    field: str,
    exclude_count: int,
) -> Optional[List[float]]:
    """Return prior-bar numeric values while excluding the latest bars from the end."""

    if window <= 0 or exclude_count <= 0 or len(bars) <= exclude_count:
        return None
    source_bars = bars[:-exclude_count]
    if len(source_bars) < window:
        return None
    values = [safe_float(bar.get(field)) for bar in source_bars[-window:]]
    if any(value is None for value in values):
        return None
    return values


def previous_highest(bars: List[Dict[str, object]], window: int) -> Optional[float]:
    """Return the highest prior-bar high from the previous window bars only."""

    highs = _previous_window_values(bars, window, "high", exclude_count=1)
    if highs is None:
        return None
    return max(highs)


def previous_lowest(bars: List[Dict[str, object]], window: int) -> Optional[float]:
    """Return the lowest prior-bar low from the previous window bars only."""

    lows = _previous_window_values(bars, window, "low", exclude_count=1)
    if lows is None:
        return None
    return min(lows)


def previous_sma(
    bars: List[Dict[str, object]],
    window: int,
    field: str = "close",
) -> Optional[float]:
    """Return the simple average from the previous window bars only."""

    values = _previous_window_values(bars, window, field, exclude_count=1)
    if values is None:
        return None
    return sum(values) / float(len(values))


def _previous_sma_with_offset(
    bars: List[Dict[str, object]],
    window: int,
    field: str,
    offset: int,
) -> Optional[float]:
    """Return a prior-bar SMA with an additional offset from the latest bar."""

    values = _previous_window_values(bars, window, field, exclude_count=1 + offset)
    if values is None:
        return None
    return sum(values) / float(len(values))


def previous_atr(bars: List[Dict[str, object]], window: int) -> Optional[float]:
    """Return the simple ATR over the previous window bars, excluding the current bar.

    The first true-range value also needs a previous close. If that previous close
    is not available from the bar before the ATR window, this function returns None.
    """

    if window <= 0:
        return None
    previous_bars = bars[:-1]
    if len(previous_bars) <= window:
        return None

    start_index = len(previous_bars) - window
    if start_index <= 0:
        return None

    true_ranges = []  # type: List[float]
    for index in range(start_index, len(previous_bars)):
        current_bar = previous_bars[index]
        previous_bar = previous_bars[index - 1]
        high = safe_float(current_bar.get("high"))
        low = safe_float(current_bar.get("low"))
        previous_close = safe_float(previous_bar.get("close"))
        if high is None or low is None or previous_close is None:
            return None
        true_range = max(
            high - low,
            abs(high - previous_close),
            abs(low - previous_close),
        )
        true_ranges.append(true_range)

    if not true_ranges:
        return None
    return sum(true_ranges) / float(len(true_ranges))


def current_atr(bars: List[Dict[str, object]], window: int) -> Optional[float]:
    """Return the legacy ATR over the latest window bars, including the current bar.

    This mirrors the research pandas implementation:
    - previous_close = close.shift(1)
    - true_range = max(high-low, abs(high-previous_close), abs(low-previous_close))
    - atr20 = true_range.rolling(window).mean()

    Pandas uses the current bar in the rolling mean and the first row falls back to
    high-low because the shifted previous close is NaN.
    """

    if window <= 0 or len(bars) < window:
        return None

    source_bars = bars[-window:]
    true_ranges = []  # type: List[float]
    offset = len(bars) - len(source_bars)
    for local_index, current_bar in enumerate(source_bars):
        global_index = offset + local_index
        high = safe_float(current_bar.get("high"))
        low = safe_float(current_bar.get("low"))
        if high is None or low is None:
            return None

        previous_close = None
        if global_index > 0:
            previous_close = safe_float(bars[global_index - 1].get("close"))

        true_range_candidates = [high - low]
        if previous_close is not None:
            true_range_candidates.append(abs(high - previous_close))
            true_range_candidates.append(abs(low - previous_close))
        true_ranges.append(max(true_range_candidates))

    if not true_ranges:
        return None
    return sum(true_ranges) / float(len(true_ranges))


def calculate_v4_indicators(
    bars: List[Dict[str, object]],
    entry_window: int = 30,
    exit_window: int = 10,
    atr_window: int = 20,
    trend_ma_window: int = 500,
) -> Dict[str, object]:
    """Calculate legacy V4-compatible indicators using prior bars only."""

    entry_high = previous_highest(bars, entry_window)
    entry_low = previous_lowest(bars, entry_window)
    exit_high = previous_highest(bars, exit_window)
    exit_low = previous_lowest(bars, exit_window)
    atr = current_atr(bars, atr_window)
    trend_ma = _previous_sma_with_offset(bars, trend_ma_window, field="close", offset=0)
    trend_ma_previous = _previous_sma_with_offset(bars, trend_ma_window, field="close", offset=1)
    trend_ma_previous_2 = _previous_sma_with_offset(bars, trend_ma_window, field="close", offset=2)

    slope_up = False
    slope_down = False
    if trend_ma is not None and trend_ma_previous is not None:
        slope_up = trend_ma > trend_ma_previous
        slope_down = trend_ma < trend_ma_previous

    channel_width = None
    channel_width_pct = None
    channel_width_atr = None
    previous_close = None
    if len(bars) > 1:
        previous_close = safe_float(bars[-2].get("close"))
    if entry_high is not None and entry_low is not None:
        channel_width = float(entry_high) - float(entry_low)
        if previous_close not in (None, 0.0):
            channel_width_pct = channel_width / float(previous_close)
        if atr not in (None, 0.0):
            channel_width_atr = channel_width / float(atr)

    indicators = {
        "entry_high": entry_high,
        "entry_low": entry_low,
        "exit_high": exit_high,
        "exit_low": exit_low,
        "atr": atr,
        "trend_ma": trend_ma,
        "trend_ma_previous": trend_ma_previous,
        "trend_ma_previous_2": trend_ma_previous_2,
        "trend_ma_slope_up": slope_up,
        "trend_ma_slope_down": slope_down,
        "channel_width": channel_width,
        "channel_width_pct": channel_width_pct,
        "channel_width_atr": channel_width_atr,
        "ready": trend_ma is not None,
        "required_bars": trend_ma_window + 1,
    }
    return indicators
