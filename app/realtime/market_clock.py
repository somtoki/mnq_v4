"""Market session timing helpers for the MNQ V4 realtime runtime."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time


@dataclass
class SessionWindow:
    """Defines a simple market session window."""

    start: time
    end: time


class MarketClock:
    """Provides session-aware helpers for realtime trading workflows."""

    def __init__(self, regular_session: SessionWindow) -> None:
        """Stores the configured market session window."""

        self._regular_session = regular_session

    def is_market_open(self, current_time: datetime) -> bool:
        """Returns whether the provided timestamp falls inside the session."""

        current_clock_time = current_time.time()
        return self._regular_session.start <= current_clock_time <= self._regular_session.end

    def can_open_new_trade(self, current_time: datetime) -> bool:
        """Returns whether new trades may be opened at the provided time."""

        return self.is_market_open(current_time)

