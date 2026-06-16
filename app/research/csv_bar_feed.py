"""CSV-based historical bar feed for paper trading and strategy wiring tests."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterator, List, Optional


RAW_MNQ_15M_COLUMN_NAMES = [
    "date",
    "time",
    "open",
    "high",
    "low",
    "close",
    "ma5",
    "ma10",
    "ma60",
    "ma120",
    "extra_indicator",
    "volume",
    "volume_ma5",
    "volume_ma20",
    "volume_ma60",
    "volume_ma120",
    "ma500",
]


class CsvBarFeed:
    """Loads historical CSV bars and yields one normalized bar dictionary at a time."""

    def __init__(self, csv_path: str, symbol: str = "MNQ") -> None:
        """Stores the CSV path and default symbol used for yielded bars."""

        self._csv_path = Path(csv_path)
        self._symbol = symbol

    def __iter__(self) -> Iterator[Dict[str, object]]:
        """Yields normalized bar dictionaries from the configured CSV file."""

        with self._csv_path.open("r", newline="", encoding="utf-8-sig") as handle:
            first_line = handle.readline()
            handle.seek(0)
            if self._looks_like_headered_csv(first_line):
                reader = csv.DictReader(handle)
                for row in reader:
                    yield self._row_to_bar(row)
                return

            reader = list(csv.reader(handle))
            for row in reversed(reader):
                yield self._raw_row_to_bar(row)

    def _row_to_bar(self, row: Dict[str, str]) -> Dict[str, object]:
        """Converts a raw CSV row into a normalized bar dictionary."""

        normalized = {str(key).strip().lower(): value for key, value in row.items() if key is not None}
        timestamp = self._get_first_value(normalized, ["datetime", "timestamp", "date"])
        if timestamp is None:
            raise ValueError("CSV row is missing a datetime/timestamp/date column.")
        volume_text = normalized.get("volume")
        volume = float(volume_text) if volume_text not in (None, "") else 0.0
        return {
            "symbol": self._symbol,
            "timestamp": str(timestamp),
            "open": float(self._require_value(normalized, "open")),
            "high": float(self._require_value(normalized, "high")),
            "low": float(self._require_value(normalized, "low")),
            "close": float(self._require_value(normalized, "close")),
            "volume": volume,
        }

    def _raw_row_to_bar(self, row: List[str]) -> Dict[str, object]:
        """Converts a headerless legacy MNQ 15-minute row into a normalized bar."""

        if len(row) < len(RAW_MNQ_15M_COLUMN_NAMES):
            raise ValueError(
                "Headerless MNQ 15-minute CSV row is missing expected columns."
            )
        normalized = {
            RAW_MNQ_15M_COLUMN_NAMES[index]: value
            for index, value in enumerate(row[: len(RAW_MNQ_15M_COLUMN_NAMES)])
        }
        timestamp = "{0} {1}".format(
            self._require_value(normalized, "date"),
            self._require_value(normalized, "time"),
        )
        timestamp = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").isoformat()
        volume_text = normalized.get("volume")
        volume = float(volume_text) if volume_text not in (None, "") else 0.0
        return {
            "symbol": self._symbol,
            "timestamp": timestamp,
            "open": float(self._require_value(normalized, "open")),
            "high": float(self._require_value(normalized, "high")),
            "low": float(self._require_value(normalized, "low")),
            "close": float(self._require_value(normalized, "close")),
            "volume": volume,
        }

    def _looks_like_headered_csv(self, first_line: str) -> bool:
        """Returns whether the file appears to start with a named header row."""

        normalized = first_line.strip().lower()
        if not normalized:
            return False
        header_tokens = [token.strip() for token in normalized.split(",")]
        expected_tokens = {"datetime", "timestamp", "date", "open", "high", "low", "close"}
        return bool(expected_tokens.intersection(header_tokens))

    def _get_first_value(self, row: Dict[str, str], keys: List[str]) -> Optional[str]:
        """Returns the first non-empty value from the provided candidate keys."""

        for key in keys:
            value = row.get(key)
            if value not in (None, ""):
                return value
        return None

    def _require_value(self, row: Dict[str, str], key: str) -> str:
        """Returns a required CSV value or raises a descriptive error."""

        value = row.get(key)
        if value in (None, ""):
            raise ValueError("CSV row is missing required column: {0}".format(key))
        return value
