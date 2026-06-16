from app.strategies.v4_indicator_helper import (
    calculate_v4_indicators,
    previous_atr,
    previous_highest,
    previous_lowest,
    previous_sma,
)


def _build_bar(index, close):
    return {
        "timestamp": "2024-01-01 00:{0:02d}:00".format(index),
        "symbol": "MNQ",
        "open": float(close - 0.5),
        "high": float(close + 1.0),
        "low": float(close - 1.0),
        "close": float(close),
        "volume": 100.0,
    }


def test_previous_highest_and_lowest_exclude_current_bar():
    bars = [
        _build_bar(0, 10.0),
        _build_bar(1, 20.0),
        _build_bar(2, 30.0),
        _build_bar(3, 40.0),
    ]
    bars[-1]["high"] = 999.0
    bars[-1]["low"] = -999.0

    assert previous_highest(bars, 2) == 31.0
    assert previous_lowest(bars, 2) == 19.0


def test_previous_sma_excludes_current_bar():
    bars = [
        _build_bar(0, 10.0),
        _build_bar(1, 20.0),
        _build_bar(2, 30.0),
        _build_bar(3, 999.0),
    ]

    assert previous_sma(bars, 2) == 25.0


def test_previous_atr_returns_none_when_prev_close_for_first_window_bar_is_missing():
    bars = [
        _build_bar(0, 10.0),
        _build_bar(1, 11.0),
        _build_bar(2, 12.0),
    ]

    assert previous_atr(bars, 2) is None


def test_previous_atr_returns_expected_value_when_enough_bars_exist():
    bars = [
        {"timestamp": "t0", "symbol": "MNQ", "open": 9.5, "high": 10.0, "low": 8.0, "close": 9.0, "volume": 1.0},
        {"timestamp": "t1", "symbol": "MNQ", "open": 10.0, "high": 12.0, "low": 9.0, "close": 11.0, "volume": 1.0},
        {"timestamp": "t2", "symbol": "MNQ", "open": 11.0, "high": 13.0, "low": 10.0, "close": 12.0, "volume": 1.0},
        {"timestamp": "t3", "symbol": "MNQ", "open": 12.0, "high": 14.0, "low": 11.0, "close": 13.0, "volume": 1.0},
    ]

    assert previous_atr(bars, 2) == 3.0


def test_calculate_v4_indicators_ready_false_when_not_enough_bars():
    bars = [
        _build_bar(0, 10.0),
        _build_bar(1, 11.0),
        _build_bar(2, 12.0),
    ]

    indicators = calculate_v4_indicators(
        bars,
        entry_window=2,
        exit_window=2,
        atr_window=2,
        trend_ma_window=5,
    )

    assert indicators["ready"] is False
    assert indicators["trend_ma"] is None


def test_trend_ma_previous_and_slope_flags():
    bars = [
        _build_bar(0, 10.0),
        _build_bar(1, 20.0),
        _build_bar(2, 30.0),
        _build_bar(3, 40.0),
        _build_bar(4, 50.0),
    ]

    indicators = calculate_v4_indicators(
        bars,
        entry_window=2,
        exit_window=2,
        atr_window=2,
        trend_ma_window=2,
    )

    assert indicators["trend_ma"] == 35.0
    assert indicators["trend_ma_previous"] == 25.0
    assert indicators["trend_ma_previous_2"] == 15.0
    assert indicators["trend_ma_slope_up"] is True
    assert indicators["trend_ma_slope_down"] is False


def test_channel_width_and_channel_width_pct_are_calculated():
    bars = [
        _build_bar(0, 10.0),
        _build_bar(1, 20.0),
        _build_bar(2, 30.0),
        _build_bar(3, 40.0),
    ]

    indicators = calculate_v4_indicators(
        bars,
        entry_window=2,
        exit_window=2,
        atr_window=2,
        trend_ma_window=2,
    )

    assert indicators["channel_width"] == 12.0
    assert indicators["channel_width_pct"] == 12.0 / 30.0
    assert indicators["channel_width_atr"] == 12.0 / 11.5
