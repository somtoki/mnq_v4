"""Normalize future Kiwoom realtime ticks into the internal tick format."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, Optional


class KiwoomTickAdapter:
    """Converts future Kiwoom-style realtime payloads into internal tick dicts."""

    _SYMBOL_KEYS = ("symbol", "code", "symbol_code", "종목코드")
    _PRICE_KEYS = ("price", "current_price", "close", "현재가", "체결가")
    _VOLUME_KEYS = ("volume", "qty", "contract_volume", "거래량", "누적거래량")
    _TIMESTAMP_KEYS = ("timestamp", "datetime", "체결시간", "timestamp_iso")
    _DATE_KEYS = ("date", "trading_date", "영업일자")
    _TIME_KEYS = ("time", "체결시간", "trade_time")

    def __init__(self, symbol: str = "MNQ") -> None:
        """Stores the default symbol used when raw ticks omit one."""

        self._symbol = symbol

    def normalize(self, raw_tick: Dict[str, object]) -> Dict[str, object]:
        """Returns the internal tick dict consumed by LiveBarFeed."""

        price_value = self._first_value(raw_tick, self._PRICE_KEYS)
        price = self._parse_price(price_value)
        volume = self._parse_volume(self._first_value(raw_tick, self._VOLUME_KEYS))
        symbol = str(self._first_value(raw_tick, self._SYMBOL_KEYS) or self._symbol)
        timestamp = self._parse_timestamp(raw_tick)
        return {
            "symbol": symbol,
            "timestamp": timestamp,
            "price": price,
            "volume": volume,
        }

    def _parse_price(self, value: object) -> float:
        """Parses price-like values and raises when parsing fails."""

        parsed = self._parse_float(value)
        if parsed is None:
            raise ValueError("Unable to parse Kiwoom tick price from value: {0!r}".format(value))
        return parsed

    def _parse_volume(self, value: object) -> float:
        """Parses volume-like values and falls back to zero for missing values."""

        parsed = self._parse_float(value)
        if parsed is None:
            return 0.0
        return parsed

    def _parse_timestamp(self, raw_tick: Dict[str, object]) -> str:
        """Builds an ISO timestamp from supported realtime payload fields."""

        direct_timestamp = self._first_value(raw_tick, self._TIMESTAMP_KEYS)
        parsed_direct = self._parse_datetime_value(direct_timestamp)
        if parsed_direct is not None:
            return parsed_direct.isoformat(timespec="seconds")

        date_value = self._first_value(raw_tick, self._DATE_KEYS)
        time_value = self._first_value(raw_tick, self._TIME_KEYS)
        combined = self._parse_date_time_pair(date_value, time_value)
        if combined is not None:
            return combined.isoformat(timespec="seconds")

        return datetime.now().replace(microsecond=0).isoformat()

    def _first_value(self, raw_tick: Dict[str, object], keys: Iterable[str]) -> Optional[object]:
        """Returns the first present non-empty value from a list of keys."""

        for key in keys:
            if key not in raw_tick:
                continue
            value = raw_tick.get(key)
            if value is None:
                continue
            if isinstance(value, str) and not value.strip():
                continue
            return value
        return None

    def _parse_float(self, value: object) -> Optional[float]:
        """Parses Kiwoom-style numeric strings with signs and commas."""

        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)

        text = str(value).strip()
        if not text:
            return None

        normalized = text.replace(",", "")
        if normalized.startswith("+"):
            normalized = normalized[1:]

        try:
            return float(normalized)
        except ValueError:
            return None

    def _parse_datetime_value(self, value: object) -> Optional[datetime]:
        """Parses a direct timestamp field if one exists."""

        if value is None:
            return None
        if isinstance(value, datetime):
            return value.replace(microsecond=0)

        text = str(value).strip()
        if not text:
            return None

        normalized = text.replace("Z", "")
        datetime_formats = (
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y%m%d%H%M%S",
            "%Y%m%d %H%M%S",
            "%Y/%m/%d %H:%M:%S",
        )
        for fmt in datetime_formats:
            try:
                return datetime.strptime(normalized, fmt)
            except ValueError:
                continue

        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None

    def _parse_date_time_pair(self, date_value: object, time_value: object) -> Optional[datetime]:
        """Parses separate date and time fields into a combined timestamp."""

        if date_value is None and time_value is None:
            return None

        if date_value is None:
            date_text = datetime.now().strftime("%Y%m%d")
        else:
            date_text = str(date_value).strip().replace("-", "").replace("/", "")
        if not date_text:
            date_text = datetime.now().strftime("%Y%m%d")

        time_text = str(time_value or "").strip().replace(":", "")
        if not time_text:
            return None

        if len(time_text) == 4:
            time_text = "{0}00".format(time_text)
        elif len(time_text) == 5:
            time_text = "0{0}".format(time_text)

        combined = "{0}{1}".format(date_text, time_text)
        for fmt in ("%Y%m%d%H%M%S",):
            try:
                return datetime.strptime(combined, fmt)
            except ValueError:
                continue
        return None
