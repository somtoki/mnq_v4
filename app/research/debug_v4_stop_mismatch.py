"""Diagnose why paper V4 exits on ATR stop earlier than research V4."""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.strategies.v4_indicator_helper import current_atr, previous_highest, previous_lowest


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


def load_csv_rows(path: Path) -> List[Dict[str, str]]:
    """Loads a CSV file into a list of dictionaries."""

    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_raw_mnq_15m(path: Path) -> List[Dict[str, object]]:
    """Loads the legacy raw MNQ 15-minute CSV in chronological order."""

    bars: List[Dict[str, object]] = []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        rows = list(reader)

    for row in reversed(rows):
        if len(row) < len(RAW_MNQ_15M_COLUMN_NAMES):
            continue
        mapped = {
            RAW_MNQ_15M_COLUMN_NAMES[index]: row[index]
            for index in range(len(RAW_MNQ_15M_COLUMN_NAMES))
        }
        timestamp = datetime.strptime(
            "{0} {1}".format(mapped["date"], mapped["time"]),
            "%Y-%m-%d %H:%M:%S",
        )
        bars.append(
            {
                "datetime": timestamp,
                "timestamp": timestamp.isoformat(),
                "open": float(mapped["open"]),
                "high": float(mapped["high"]),
                "low": float(mapped["low"]),
                "close": float(mapped["close"]),
                "volume": float(mapped["volume"] or 0.0),
            }
        )
    return bars


def normalize_research_trade(row: Dict[str, str]) -> Dict[str, object]:
    """Normalizes research trade CSV rows."""

    return {
        "entry_time": str(row.get("entry_time", "")).strip().replace(" ", "T"),
        "exit_time": str(row.get("exit_time", "")).strip().replace(" ", "T"),
        "direction": str(row.get("direction", "")).strip().lower(),
        "entry_price": float(row.get("entry_price", "0") or 0.0),
        "exit_price": float(row.get("exit_price", "0") or 0.0),
        "exit_reason": str(row.get("exit_reason", "")).strip(),
        "pnl": float(row.get("pnl_dollars", "0") or 0.0),
        "atr_at_entry": _safe_float(row.get("atr_at_entry", "")),
        "stop_price": _safe_float(row.get("stop_price", "")),
    }


def normalize_paper_trade(row: Dict[str, str]) -> Dict[str, object]:
    """Normalizes paper trade CSV rows."""

    return {
        "entry_time": str(row.get("entry_time", "")).strip(),
        "exit_time": str(row.get("exit_time", "")).strip(),
        "direction": str(row.get("side", "")).strip().lower(),
        "entry_price": float(row.get("entry_price", "0") or 0.0),
        "exit_price": float(row.get("exit_price", "0") or 0.0),
        "exit_reason": str(row.get("exit_reason", "")).strip(),
        "pnl": float(row.get("pnl_usd", "0") or 0.0),
    }


def _safe_float(value: object) -> Optional[float]:
    """Converts a value to float when possible."""

    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_metadata(raw_metadata: str) -> Dict[str, object]:
    """Parses order execution metadata safely."""

    if not raw_metadata:
        return {}
    try:
        return json.loads(raw_metadata)
    except json.JSONDecodeError:
        return {}


def build_trade_map(
    rows: List[Dict[str, str]],
    normalizer,
) -> Dict[Tuple[str, str], Dict[str, object]]:
    """Builds a lookup by entry_time and direction."""

    result: Dict[Tuple[str, str], Dict[str, object]] = {}
    for row in rows:
        trade = normalizer(row)
        key = (str(trade["entry_time"]), str(trade["direction"]))
        result[key] = trade
    return result


def load_paper_execution_map(
    rows: List[Dict[str, str]],
) -> Dict[Tuple[str, str], Dict[str, object]]:
    """Indexes paper entry executions by entry_time and direction."""

    execution_map: Dict[Tuple[str, str], Dict[str, object]] = {}
    for row in rows:
        signal_type = str(row.get("signal_type", "")).strip()
        if signal_type not in {"LONG_ENTRY", "SHORT_ENTRY"}:
            continue
        if str(row.get("status", "")).strip() != "executed":
            continue
        direction = "long" if signal_type == "LONG_ENTRY" else "short"
        metadata = _parse_metadata(str(row.get("metadata", "")))
        key = (str(row.get("bar_timestamp", "")).strip(), direction)
        execution_map[key] = {
            "execution_price": _safe_float(row.get("execution_price", "")),
            "atr_at_entry": _safe_float(metadata.get("atr_at_entry")),
            "initial_stop_price": _safe_float(metadata.get("initial_stop_price")),
            "metadata": metadata,
        }
    return execution_map


def find_bar_index(bars: List[Dict[str, object]], timestamp_text: str) -> int:
    """Finds the bar index for a timestamp string."""

    target = datetime.fromisoformat(timestamp_text)
    for index, bar in enumerate(bars):
        if bar["datetime"] == target:
            return index
    raise ValueError("Could not find bar for timestamp: {0}".format(timestamp_text))


def sanitize_filename(value: str) -> str:
    """Sanitizes a string for use in a filename."""

    return (
        value.replace(":", "-")
        .replace("/", "-")
        .replace("\\", "-")
        .replace(" ", "_")
    )


def write_csv(path: Path, fieldnames: List[str], rows: List[Dict[str, object]]) -> None:
    """Writes rows to a CSV file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    """Creates stop-mismatch debug artifacts for the top 10 cases."""

    project_root = PROJECT_ROOT
    desktop_root = project_root.parent
    historical_path = project_root / "data" / "historical" / "15min.csv"
    paper_trades_path = project_root / "data" / "paper" / "trades.csv"
    order_executions_path = project_root / "data" / "paper" / "order_executions.csv"
    matched_diff_path = project_root / "reports" / "v4_trade_comparison" / "matched_trade_diff.csv"
    output_dir = project_root / "reports" / "v4_trade_comparison" / "stop_mismatch_debug"
    research_trades_path = (
        desktop_root
        / "autotrade"
        / "mnq_research"
        / "data"
        / "results"
        / "turtle_v4_mnq_15m"
        / "all"
        / "trades.csv"
    )

    bars = load_raw_mnq_15m(historical_path)
    research_map = build_trade_map(load_csv_rows(research_trades_path), normalize_research_trade)
    paper_map = build_trade_map(load_csv_rows(paper_trades_path), normalize_paper_trade)
    paper_execution_map = load_paper_execution_map(load_csv_rows(order_executions_path))
    matched_rows = load_csv_rows(matched_diff_path)

    selected_rows = [
        row
        for row in matched_rows
        if str(row.get("research_exit_reason", "")).strip() == "opposite_10"
        and "atr_stop" in str(row.get("paper_exit_reason", "")).strip()
    ][:10]

    output_dir.mkdir(parents=True, exist_ok=True)
    summary_lines = [
        "# Stop Mismatch Debug Summary",
        "",
        "Selected top 10 mismatches where research exited on `opposite_10` and paper exited on `atr_stop`.",
        "",
    ]

    category_counts: Dict[str, int] = {}

    for rank, row in enumerate(selected_rows, start=1):
        key = (str(row.get("entry_time", "")).strip(), str(row.get("direction", "")).strip().lower())
        research_trade = research_map[key]
        paper_trade = paper_map[key]
        paper_execution = paper_execution_map.get(key, {})

        paper_atr_at_entry = _safe_float(paper_execution.get("atr_at_entry"))
        paper_entry_price = _safe_float(paper_execution.get("execution_price"))
        paper_initial_stop_price = _safe_float(paper_execution.get("initial_stop_price"))
        if paper_entry_price is None:
            paper_entry_price = float(paper_trade["entry_price"])
        if paper_initial_stop_price is None and paper_atr_at_entry is not None:
            if str(paper_trade["direction"]) == "long":
                paper_initial_stop_price = float(paper_entry_price) - (2.0 * paper_atr_at_entry)
            else:
                paper_initial_stop_price = float(paper_entry_price) + (2.0 * paper_atr_at_entry)

        research_entry_price = float(research_trade["entry_price"])
        research_exit_price = float(research_trade["exit_price"])
        paper_exit_price = float(paper_trade["exit_price"])
        research_atr = _safe_float(research_trade.get("atr_at_entry"))
        research_stop_price = _safe_float(research_trade.get("stop_price"))

        note_prefix = ""
        if research_atr is None or research_stop_price is None:
            entry_index = find_bar_index(bars, str(research_trade["entry_time"]))
            entry_signal_index = max(entry_index - 1, 0)
            approximate_atr = current_atr(bars[: entry_signal_index + 1], 20)
            if research_atr is None:
                research_atr = approximate_atr
            if research_stop_price is None and approximate_atr is not None:
                if str(research_trade["direction"]) == "long":
                    research_stop_price = research_entry_price - (2.0 * approximate_atr)
                else:
                    research_stop_price = research_entry_price + (2.0 * approximate_atr)
            note_prefix = "research_stop_approximate;"

        entry_index = find_bar_index(bars, str(research_trade["entry_time"]))
        research_exit_index = find_bar_index(bars, str(research_trade["exit_time"]))
        paper_exit_index = find_bar_index(bars, str(paper_trade["exit_time"]))
        earlier_exit_index = min(research_exit_index, paper_exit_index)
        start_index = max(entry_index - 20, 0)
        end_index = min(earlier_exit_index + 20, len(bars) - 1)

        debug_rows: List[Dict[str, object]] = []
        stop_touched_before_research_exit = False

        for global_index in range(start_index, end_index + 1):
            bar = bars[global_index]
            prefix_bars = bars[: global_index + 1]
            rolling_low_10 = previous_lowest(prefix_bars, 10)
            rolling_high_10 = previous_highest(prefix_bars, 10)
            atr20 = current_atr(prefix_bars, 20)

            within_paper_trade = entry_index <= global_index <= paper_exit_index
            paper_stop_touched: object = ""
            paper_opposite_touched: object = ""
            if within_paper_trade and paper_initial_stop_price is not None:
                if str(paper_trade["direction"]) == "long":
                    paper_stop_touched = float(bar["low"]) <= float(paper_initial_stop_price)
                else:
                    paper_stop_touched = float(bar["high"]) >= float(paper_initial_stop_price)
            if within_paper_trade and rolling_low_10 is not None and rolling_high_10 is not None:
                if str(paper_trade["direction"]) == "long":
                    paper_opposite_touched = float(bar["close"]) < float(rolling_low_10)
                else:
                    paper_opposite_touched = float(bar["close"]) > float(rolling_high_10)

            if (
                global_index <= research_exit_index
                and paper_stop_touched is True
            ):
                stop_touched_before_research_exit = True

            notes = []
            if note_prefix:
                notes.append(note_prefix.rstrip(";"))
            if global_index == entry_index:
                notes.append("entry_bar")
            if global_index == research_exit_index:
                notes.append("research_exit_bar")
            if global_index == paper_exit_index:
                notes.append("paper_exit_bar")
            if paper_stop_touched is True:
                notes.append("paper_stop_touched")
            if paper_opposite_touched is True:
                notes.append("paper_opposite_10_touched")

            debug_rows.append(
                {
                    "datetime": str(bar["timestamp"]),
                    "open": bar["open"],
                    "high": bar["high"],
                    "low": bar["low"],
                    "close": bar["close"],
                    "side": paper_trade["direction"],
                    "research_entry_time": research_trade["entry_time"],
                    "research_exit_time": research_trade["exit_time"],
                    "research_entry_price": research_entry_price,
                    "research_exit_price": research_exit_price,
                    "research_exit_reason": research_trade["exit_reason"],
                    "paper_entry_time": paper_trade["entry_time"],
                    "paper_exit_time": paper_trade["exit_time"],
                    "paper_entry_price": paper_entry_price,
                    "paper_exit_price": paper_exit_price,
                    "paper_exit_reason": paper_trade["exit_reason"],
                    "research_atr_at_entry_if_available": research_atr if research_atr is not None else "",
                    "paper_atr_at_entry": paper_atr_at_entry if paper_atr_at_entry is not None else "",
                    "research_stop_price_if_available": (
                        research_stop_price if research_stop_price is not None else ""
                    ),
                    "paper_initial_stop_price": (
                        paper_initial_stop_price if paper_initial_stop_price is not None else ""
                    ),
                    "paper_stop_touched": paper_stop_touched,
                    "paper_opposite_10_touched": paper_opposite_touched,
                    "rolling_low_10": rolling_low_10 if rolling_low_10 is not None else "",
                    "rolling_high_10": rolling_high_10 if rolling_high_10 is not None else "",
                    "atr20": atr20 if atr20 is not None else "",
                    "note": ";".join(notes),
                }
            )

        entry_time_match = str(research_trade["entry_time"]) == str(paper_trade["entry_time"])
        entry_price_match = abs(float(research_entry_price) - float(paper_entry_price)) < 1e-9
        atr_match = (
            research_atr is not None
            and paper_atr_at_entry is not None
            and abs(float(research_atr) - float(paper_atr_at_entry)) < 1e-9
        )

        if not entry_time_match:
            likely_cause = "different entry time"
        elif not entry_price_match:
            likely_cause = "different entry price"
        elif (
            research_atr is not None
            and paper_atr_at_entry is not None
            and abs(float(research_atr) - float(paper_atr_at_entry)) >= 1e-9
        ):
            likely_cause = "same entry, stop calc mismatch"
        elif stop_touched_before_research_exit:
            likely_cause = "same entry, stop trigger mismatch"
        else:
            likely_cause = "unknown"

        category_counts[likely_cause] = category_counts.get(likely_cause, 0) + 1

        filename = "{0:02d}_{1}_{2}.csv".format(
            rank,
            sanitize_filename(str(research_trade["entry_time"])),
            str(research_trade["direction"]),
        )
        write_csv(
            output_dir / filename,
            [
                "datetime",
                "open",
                "high",
                "low",
                "close",
                "side",
                "research_entry_time",
                "research_exit_time",
                "research_entry_price",
                "research_exit_price",
                "research_exit_reason",
                "paper_entry_time",
                "paper_exit_time",
                "paper_entry_price",
                "paper_exit_price",
                "paper_exit_reason",
                "research_atr_at_entry_if_available",
                "paper_atr_at_entry",
                "research_stop_price_if_available",
                "paper_initial_stop_price",
                "paper_stop_touched",
                "paper_opposite_10_touched",
                "rolling_low_10",
                "rolling_high_10",
                "atr20",
                "note",
            ],
            debug_rows,
        )

        summary_lines.extend(
            [
                "## {0}. {1} {2}".format(rank, research_trade["entry_time"], research_trade["direction"]),
                "",
                "- research_exit_reason: `{0}`".format(research_trade["exit_reason"]),
                "- paper_exit_reason: `{0}`".format(paper_trade["exit_reason"]),
                "- research_exit_time: `{0}`".format(research_trade["exit_time"]),
                "- paper_exit_time: `{0}`".format(paper_trade["exit_time"]),
                "- paper entry_price matches research entry_price: `{0}`".format(entry_price_match),
                "- paper entry_time matches research entry_time: `{0}`".format(entry_time_match),
                "- paper atr_at_entry appears different: `{0}`".format(not atr_match),
                "- paper stop price was actually touched before research exit: `{0}`".format(
                    stop_touched_before_research_exit
                ),
                "- likely cause: `{0}`".format(likely_cause),
                "",
            ]
        )

    summary_lines.extend(
        [
            "## Cause Counts",
            "",
        ]
    )
    for cause, count in sorted(category_counts.items(), key=lambda item: (-item[1], item[0])):
        summary_lines.append("- `{0}`: {1}".format(cause, count))

    summary_path = output_dir / "summary.md"
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    print("Debug output directory: {0}".format(output_dir))
    print("Selected mismatches: {0}".format(len(selected_rows)))
    for cause, count in sorted(category_counts.items(), key=lambda item: (-item[1], item[0])):
        print("Cause {0}: {1}".format(cause, count))


if __name__ == "__main__":
    main()
