"""Diagnose remaining unmatched research vs paper V4 trades."""

from __future__ import annotations

import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


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
BLOCKED_ENTRY_HOURS = {15, 16, 17}


def load_csv_rows(path: Path) -> List[Dict[str, str]]:
    """Loads CSV rows."""

    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def load_raw_bars(path: Path) -> List[Dict[str, object]]:
    """Loads raw 15-minute bars in chronological order."""

    bars: List[Dict[str, object]] = []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))

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
            }
        )
    return bars


def load_trade_map(path: Path, source: str) -> Dict[Tuple[str, str], Dict[str, object]]:
    """Loads research or paper trades keyed by entry_time and direction."""

    rows = load_csv_rows(path)
    result: Dict[Tuple[str, str], Dict[str, object]] = {}
    for row in rows:
        if source == "research":
            direction = str(row.get("direction", "")).strip().lower()
            pnl = float(row.get("pnl_dollars", "0") or 0.0)
            entry_price = float(row.get("entry_price", "0") or 0.0)
            exit_price = float(row.get("exit_price", "0") or 0.0)
            exit_time = str(row.get("exit_time", "")).strip().replace(" ", "T")
            exit_reason = str(row.get("exit_reason", "")).strip()
        else:
            direction = str(row.get("side", "")).strip().lower()
            pnl = float(row.get("pnl_usd", "0") or 0.0)
            entry_price = float(row.get("entry_price", "0") or 0.0)
            exit_price = float(row.get("exit_price", "0") or 0.0)
            exit_time = str(row.get("exit_time", "")).strip()
            exit_reason = str(row.get("exit_reason", "")).strip()
        entry_time = str(row.get("entry_time", "")).strip().replace(" ", "T")
        key = (entry_time, direction)
        result[key] = {
            "entry_time": entry_time,
            "direction": direction,
            "pnl": pnl,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "exit_time": exit_time,
            "exit_reason": exit_reason,
        }
    return result


def find_bar_index_map(bars: List[Dict[str, object]]) -> Dict[str, int]:
    """Builds a timestamp-to-index lookup."""

    return {
        str(bar["timestamp"]): index
        for index, bar in enumerate(bars)
    }


def classify_near_match(
    source_trade: Dict[str, object],
    candidate: Optional[Dict[str, object]],
    bar_index_map: Dict[str, int],
    reverse_side_candidates: List[Dict[str, object]],
) -> Tuple[str, Optional[int], str]:
    """Classifies one unmatched trade against its nearest counterpart."""

    source_entry_time = str(source_trade["entry_time"])
    source_direction = str(source_trade["direction"])
    source_index = bar_index_map.get(source_entry_time)
    if source_index is None:
        return "unknown", None, "entry_time_not_found_in_bars"

    if candidate is None:
        side_conflict = _find_side_conflict(source_index, reverse_side_candidates, bar_index_map)
        if side_conflict:
            return "side_conflict", side_conflict[0], "opposite_side_within_5_bars"
        next_bar_hour = _get_next_bar_hour(source_index, bar_index_map)
        if next_bar_hour in BLOCKED_ENTRY_HOURS:
            return "possible_entry_hour_block", None, "next_bar_hour_in_blocked_entry_hours"
        return "no_near_match", None, "no_same_side_trade_within_5_bars"

    candidate_entry_time = str(candidate["entry_time"])
    candidate_index = bar_index_map.get(candidate_entry_time)
    if candidate_index is None:
        return "unknown", None, "candidate_entry_time_not_found_in_bars"

    bar_delta = candidate_index - source_index
    if abs(bar_delta) == 1:
        return "near_match_entry_shift", bar_delta, "same_side_trade_within_1_bar"

    source_exit_index = bar_index_map.get(str(source_trade["exit_time"]))
    candidate_exit_index = bar_index_map.get(str(candidate["exit_time"]))
    if source_exit_index is not None and candidate_exit_index is not None:
        exit_delta = candidate_exit_index - source_exit_index
        if abs(exit_delta) == 1:
            return "near_match_exit_shift", exit_delta, "exit_times_within_1_bar"

    if (
        abs(float(source_trade["entry_price"]) - float(candidate["entry_price"])) > 1e-9
        or abs(float(source_trade["exit_price"]) - float(candidate["exit_price"])) > 1e-9
    ):
        return "near_match_price_diff", bar_delta, "same_side_trade_within_5_bars_but_price_diff"

    return "unknown", bar_delta, "same_side_trade_within_5_bars_without_simple_shift_pattern"


def _find_same_side_candidate(
    source_trade: Dict[str, object],
    candidate_trades: List[Dict[str, object]],
    bar_index_map: Dict[str, int],
) -> Optional[Dict[str, object]]:
    """Finds the nearest same-side candidate within +/- 5 bars."""

    source_index = bar_index_map.get(str(source_trade["entry_time"]))
    if source_index is None:
        return None

    best_candidate = None
    best_distance = None
    for trade in candidate_trades:
        if str(trade["direction"]) != str(source_trade["direction"]):
            continue
        candidate_index = bar_index_map.get(str(trade["entry_time"]))
        if candidate_index is None:
            continue
        distance = abs(candidate_index - source_index)
        if distance > 5:
            continue
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_candidate = trade
    return best_candidate


def _find_side_conflict(
    source_index: int,
    candidate_trades: List[Dict[str, object]],
    bar_index_map: Dict[str, int],
) -> Optional[Tuple[int, Dict[str, object]]]:
    """Returns an opposite-side nearby trade if one exists."""

    best = None
    best_distance = None
    for trade in candidate_trades:
        candidate_index = bar_index_map.get(str(trade["entry_time"]))
        if candidate_index is None:
            continue
        distance = abs(candidate_index - source_index)
        if distance > 5:
            continue
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best = trade
    if best is None or best_distance is None:
        return None
    return best_distance, best


def _get_next_bar_hour(source_index: int, bar_index_map: Dict[str, int]) -> Optional[int]:
    """Returns the next bar hour for a source index if available."""

    reverse_lookup = {index: timestamp for timestamp, index in bar_index_map.items()}
    next_timestamp = reverse_lookup.get(source_index + 1)
    if next_timestamp is None:
        return None
    return datetime.fromisoformat(next_timestamp).hour


def write_csv(path: Path, fieldnames: List[str], rows: List[Dict[str, object]]) -> None:
    """Writes CSV rows."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_near_match_rows(
    source_trades: List[Dict[str, object]],
    candidate_trades: List[Dict[str, object]],
    bar_index_map: Dict[str, int],
) -> Tuple[List[Dict[str, object]], Dict[str, int]]:
    """Builds nearest-match rows plus classification counts."""

    rows: List[Dict[str, object]] = []
    counts: Dict[str, int] = {}
    for trade in source_trades:
        candidate = _find_same_side_candidate(trade, candidate_trades, bar_index_map)
        reverse_side_candidates = [
            other for other in candidate_trades
            if str(other["direction"]) != str(trade["direction"])
        ]
        classification, bar_delta, note = classify_near_match(
            trade,
            candidate,
            bar_index_map,
            reverse_side_candidates,
        )
        counts[classification] = counts.get(classification, 0) + 1
        rows.append(
            {
                "entry_time": trade["entry_time"],
                "direction": trade["direction"],
                "pnl": trade["pnl"],
                "classification": classification,
                "candidate_entry_time": candidate["entry_time"] if candidate is not None else "",
                "candidate_direction": candidate["direction"] if candidate is not None else "",
                "candidate_pnl": candidate["pnl"] if candidate is not None else "",
                "source_exit_time": trade["exit_time"],
                "candidate_exit_time": candidate["exit_time"] if candidate is not None else "",
                "source_entry_price": trade["entry_price"],
                "candidate_entry_price": candidate["entry_price"] if candidate is not None else "",
                "source_exit_price": trade["exit_price"],
                "candidate_exit_price": candidate["exit_price"] if candidate is not None else "",
                "source_exit_reason": trade["exit_reason"],
                "candidate_exit_reason": candidate["exit_reason"] if candidate is not None else "",
                "entry_bar_delta": bar_delta if bar_delta is not None else "",
                "note": note,
            }
        )
    return rows, counts


def load_full_trade_list(path: Path, source: str) -> List[Dict[str, object]]:
    """Loads all trades as a list."""

    return list(load_trade_map(path, source).values())


def main() -> None:
    """Diagnoses unmatched research-only and paper-only trades."""

    output_dir = PROJECT_ROOT / "reports" / "v4_trade_comparison" / "unmatched_diagnosis"
    research_only_path = PROJECT_ROOT / "reports" / "v4_trade_comparison" / "research_only_trades.csv"
    paper_only_path = PROJECT_ROOT / "reports" / "v4_trade_comparison" / "paper_only_trades.csv"
    matched_diff_path = PROJECT_ROOT / "reports" / "v4_trade_comparison" / "matched_trade_diff.csv"
    historical_path = PROJECT_ROOT / "data" / "historical" / "15min.csv"
    research_trades_path = (
        PROJECT_ROOT.parent
        / "autotrade"
        / "mnq_research"
        / "data"
        / "results"
        / "turtle_v4_mnq_15m"
        / "all"
        / "trades.csv"
    )
    paper_trades_path = PROJECT_ROOT / "data" / "paper" / "trades.csv"

    _ = load_csv_rows(matched_diff_path)
    bars = load_raw_bars(historical_path)
    bar_index_map = find_bar_index_map(bars)

    research_only_seed = load_csv_rows(research_only_path)
    paper_only_seed = load_csv_rows(paper_only_path)
    research_trade_map = load_trade_map(research_trades_path, "research")
    paper_trade_map = load_trade_map(paper_trades_path, "paper")

    research_only_trades = [
        research_trade_map[(str(row["entry_time"]), str(row["direction"]))]
        for row in research_only_seed
        if (str(row["entry_time"]), str(row["direction"])) in research_trade_map
    ]
    paper_only_trades = [
        paper_trade_map[(str(row["entry_time"]), str(row["direction"]))]
        for row in paper_only_seed
        if (str(row["entry_time"]), str(row["direction"])) in paper_trade_map
    ]

    research_rows, research_counts = build_near_match_rows(
        research_only_trades,
        paper_only_trades,
        bar_index_map,
    )
    paper_rows, paper_counts = build_near_match_rows(
        paper_only_trades,
        research_only_trades,
        bar_index_map,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "entry_time",
        "direction",
        "pnl",
        "classification",
        "candidate_entry_time",
        "candidate_direction",
        "candidate_pnl",
        "source_exit_time",
        "candidate_exit_time",
        "source_entry_price",
        "candidate_entry_price",
        "source_exit_price",
        "candidate_exit_price",
        "source_exit_reason",
        "candidate_exit_reason",
        "entry_bar_delta",
        "note",
    ]
    write_csv(output_dir / "research_only_near_matches.csv", fieldnames, research_rows)
    write_csv(output_dir / "paper_only_near_matches.csv", fieldnames, paper_rows)

    summary_lines = [
        "# Unmatched V4 Trade Diagnosis",
        "",
        "## Research Only Classification Counts",
        "",
    ]
    for classification, count in sorted(research_counts.items(), key=lambda item: (-item[1], item[0])):
        summary_lines.append("- `{0}`: {1}".format(classification, count))

    summary_lines.extend(
        [
            "",
            "## Paper Only Classification Counts",
            "",
        ]
    )
    for classification, count in sorted(paper_counts.items(), key=lambda item: (-item[1], item[0])):
        summary_lines.append("- `{0}`: {1}".format(classification, count))

    summary_lines.extend(
        [
            "",
            "## Top 10 Research Only Examples",
            "",
        ]
    )
    for row in research_rows[:10]:
        summary_lines.append(
            "- `{0}` `{1}` -> `{2}` candidate `{3}` note `{4}`".format(
                row["entry_time"],
                row["direction"],
                row["classification"],
                row["candidate_entry_time"] or "None",
                row["note"],
            )
        )

    summary_lines.extend(
        [
            "",
            "## Top 10 Paper Only Examples",
            "",
        ]
    )
    for row in paper_rows[:10]:
        summary_lines.append(
            "- `{0}` `{1}` -> `{2}` candidate `{3}` note `{4}`".format(
                row["entry_time"],
                row["direction"],
                row["classification"],
                row["candidate_entry_time"] or "None",
                row["note"],
            )
        )

    near_shift_total = (
        research_counts.get("near_match_entry_shift", 0)
        + research_counts.get("near_match_exit_shift", 0)
        + paper_counts.get("near_match_entry_shift", 0)
        + paper_counts.get("near_match_exit_shift", 0)
    )
    logic_mismatch_total = (
        research_counts.get("no_near_match", 0)
        + research_counts.get("possible_entry_hour_block", 0)
        + research_counts.get("side_conflict", 0)
        + paper_counts.get("no_near_match", 0)
        + paper_counts.get("possible_entry_hour_block", 0)
        + paper_counts.get("side_conflict", 0)
    )
    if near_shift_total >= logic_mismatch_total:
        overall_view = "most remaining differences look closer to comparison matching issue"
        next_fix = "add tolerant matching that allows +/-1 bar entry alignment before classifying trades as unmatched"
    else:
        overall_view = "most remaining differences look closer to true logic mismatch"
        next_fix = "inspect research_only and paper_only near-match clusters around blocked entry hours and one-bar timing drift"

    summary_lines.extend(
        [
            "",
            "## Overall Assessment",
            "",
            "- {0}".format(overall_view),
            "- Specific next fix recommendation: {0}".format(next_fix),
            "",
        ]
    )

    (output_dir / "summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    print("Output directory: {0}".format(output_dir))
    print("Research classifications: {0}".format(research_counts))
    print("Paper classifications: {0}".format(paper_counts))


if __name__ == "__main__":
    main()
