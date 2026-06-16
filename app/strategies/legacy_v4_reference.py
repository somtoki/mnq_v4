"""Reference skeleton for migrating the legacy Turtle V4 research strategy.

This module is intentionally non-executable. It captures the structure and
interfaces that will likely be needed when porting the research strategy from
`autotrade\mnq_research` into the realtime-friendly `mnq_v4` project.
"""

from __future__ import annotations

from typing import Dict, List, Optional


class LegacyV4Reference:
    """Comment-oriented reference shell for the legacy Turtle V4 strategy."""

    def prepare_indicators(self, bars: List[Dict[str, object]]) -> Dict[str, object]:
        """Prepare prior-bar Donchian, ATR20, and trend-MA500 style values.

        Expected inputs:
        - sequential 15-minute MNQ bars
        - each bar contains timestamp/open/high/low/close/volume

        Expected outputs:
        - entry channel highs/lows based on prior bars only
        - exit channel highs/lows based on prior bars only
        - ATR(20) equivalent
        - trend MA(500) equivalent
        """

        raise NotImplementedError

    def evaluate_entry(self, bar: Dict[str, object], indicators: Dict[str, object]) -> Dict[str, bool]:
        """Evaluate long/short entry eligibility.

        Legacy V4 reference points:
        - long breakout uses close > entry_high
        - short breakout uses close < entry_low
        - MA500 slope filter is asymmetric
        - long side has channel-width exceptions
        - entry is suppressed if next bar hour is in {15,16,17}
        - no overlapping positions allowed
        """

        raise NotImplementedError

    def evaluate_exit(
        self,
        bar: Dict[str, object],
        indicators: Dict[str, object],
        position_state: Dict[str, object],
    ) -> Dict[str, bool]:
        """Evaluate exit eligibility for an existing position.

        Legacy V4 reference points:
        - ATR stop is checked from intrabar high/low
        - opposite_10 exit uses close vs prior-bar 10-channel
        - trigger is detected on current bar
        - fill is modeled at next bar open in research code
        """

        raise NotImplementedError

    def compute_next_bar_fill(
        self,
        next_bar: Dict[str, object],
        direction: str,
        slippage: float,
    ) -> float:
        """Model the next-bar-open fill convention used by research V4."""

        raise NotImplementedError

    def build_position_state(
        self,
        entry_bar: Dict[str, object],
        entry_price: float,
        atr_at_entry: float,
    ) -> Dict[str, object]:
        """Create the minimal state needed for one-position-at-a-time tracking.

        Suggested state fields:
        - direction
        - entry_time
        - entry_price
        - atr_at_entry
        - stop_price
        - entry_index
        - max_favorable_points
        - exit_reason
        """

        raise NotImplementedError


LEGACY_V4_PORT_NOTES = {
    "wrapper": "turtle_strategy_v4.py only adds blocked_entry_hours={15,16,17}",
    "core_logic": "turtle_strategy_v3.py -> turtle_strategy_v2.py",
    "indicator_source": "app/indicators/turtle.py",
    "research_runner": "app/research/run_turtle_v4_mnq_15m.py",
    "must_match_fill_model": "signal on current close, fill on next bar open",
}
