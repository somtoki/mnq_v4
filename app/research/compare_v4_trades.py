"""Compare canonical research V4 trades against paper V4 trades."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


BAR_MINUTES = 15


def parse_args() -> argparse.Namespace:
    """Parses comparison CLI arguments."""

    project_root = Path(__file__).resolve().parents[2]
    desktop_root = project_root.parent
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--research",
        default=str(
            desktop_root
            / "autotrade"
            / "mnq_research"
            / "data"
            / "results"
            / "turtle_v4_mnq_15m"
            / "all"
            / "trades.csv"
        ),
        help="Path to research trades.csv",
    )
    parser.add_argument(
        "--paper",
        default=str(project_root / "data" / "paper" / "trades.csv"),
        help="Path to paper trades.csv",
    )
    parser.add_argument(
        "--output-dir",
        default=str(project_root / "reports" / "v4_trade_comparison"),
        help="Directory for comparison CSVs",
    )
    return parser.parse_args()


def load_csv_rows(path: Path) -> List[Dict[str, str]]:
    """Loads CSV rows into memory."""

    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _parse_time(value: str) -> datetime:
    """Parses either spaced or ISO timestamps."""

    return datetime.fromisoformat(value.strip().replace(" ", "T"))


def normalize_research_trade(row: Dict[str, str], index: int) -> Dict[str, object]:
    """Normalizes one research trade row into a common comparison schema."""

    entry_time = str(row.get("entry_time", "")).strip().replace(" ", "T")
    exit_time = str(row.get("exit_time", "")).strip().replace(" ", "T")
    return {
        "id": "research-{0}".format(index),
        "source": "research",
        "entry_time": entry_time,
        "entry_dt": _parse_time(entry_time),
        "direction": str(row.get("direction", "")).strip().lower(),
        "exit_time": exit_time,
        "exit_dt": _parse_time(exit_time),
        "exit_reason": str(row.get("exit_reason", "")).strip(),
        "pnl": float(row.get("pnl_dollars", "0") or 0.0),
        "entry_price": float(row.get("entry_price", "0") or 0.0),
        "exit_price": float(row.get("exit_price", "0") or 0.0),
    }


def normalize_paper_trade(row: Dict[str, str], index: int) -> Dict[str, object]:
    """Normalizes one paper trade row into a common comparison schema."""

    entry_time = str(row.get("entry_time", "")).strip()
    exit_time = str(row.get("exit_time", "")).strip()
    return {
        "id": "paper-{0}".format(index),
        "source": "paper",
        "entry_time": entry_time,
        "entry_dt": _parse_time(entry_time),
        "direction": str(row.get("side", "")).strip().lower(),
        "exit_time": exit_time,
        "exit_dt": _parse_time(exit_time),
        "exit_reason": str(row.get("exit_reason", "")).strip(),
        "pnl": float(row.get("pnl_usd", "0") or 0.0),
        "entry_price": float(row.get("entry_price", "0") or 0.0),
        "exit_price": float(row.get("exit_price", "0") or 0.0),
    }


def load_trades(path: Path, source: str) -> List[Dict[str, object]]:
    """Loads and normalizes trade rows."""

    rows = load_csv_rows(path)
    trades: List[Dict[str, object]] = []
    for index, row in enumerate(rows):
        if source == "research":
            trades.append(normalize_research_trade(row, index))
        else:
            trades.append(normalize_paper_trade(row, index))
    return trades


def write_csv(path: Path, fieldnames: List[str], rows: List[Dict[str, object]]) -> None:
    """Writes rows to a CSV file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def exact_match_trades(
    research_trades: List[Dict[str, object]],
    paper_trades: List[Dict[str, object]],
) -> Tuple[List[Tuple[Dict[str, object], Dict[str, object], str]], List[Dict[str, object]], List[Dict[str, object]]]:
    """Performs exact matching on same side and exact entry_time."""

    paper_by_key: Dict[Tuple[str, str], List[Dict[str, object]]] = {}
    for trade in paper_trades:
        key = (str(trade["entry_time"]), str(trade["direction"]))
        paper_by_key.setdefault(key, []).append(trade)

    matched: List[Tuple[Dict[str, object], Dict[str, object], str]] = []
    unmatched_research: List[Dict[str, object]] = []
    matched_paper_ids = set()

    for trade in research_trades:
        key = (str(trade["entry_time"]), str(trade["direction"]))
        candidates = paper_by_key.get(key, [])
        candidate = next((item for item in candidates if item["id"] not in matched_paper_ids), None)
        if candidate is None:
            unmatched_research.append(trade)
            continue
        matched_paper_ids.add(str(candidate["id"]))
        matched.append((trade, candidate, "exact"))

    unmatched_paper = [trade for trade in paper_trades if trade["id"] not in matched_paper_ids]
    return matched, unmatched_research, unmatched_paper


def fuzzy_match_trades(
    research_trades: List[Dict[str, object]],
    paper_trades: List[Dict[str, object]],
) -> Tuple[List[Tuple[Dict[str, object], Dict[str, object], str]], List[Dict[str, object]], List[Dict[str, object]]]:
    """Performs fuzzy entry matching within +/- 1 bar on same side."""

    matched: List[Tuple[Dict[str, object], Dict[str, object], str]] = []
    matched_paper_ids = set()
    unmatched_research: List[Dict[str, object]] = []

    for research_trade in research_trades:
        candidates: List[Tuple[int, int, Dict[str, object]]] = []
        for paper_trade in paper_trades:
            if paper_trade["id"] in matched_paper_ids:
                continue
            if str(research_trade["direction"]) != str(paper_trade["direction"]):
                continue
            entry_diff_minutes = int(
                abs((paper_trade["entry_dt"] - research_trade["entry_dt"]).total_seconds() // 60)
            )
            if entry_diff_minutes > BAR_MINUTES:
                continue
            exit_diff_minutes = int(
                abs((paper_trade["exit_dt"] - research_trade["exit_dt"]).total_seconds() // 60)
            )
            candidates.append((entry_diff_minutes, exit_diff_minutes, paper_trade))

        if not candidates:
            unmatched_research.append(research_trade)
            continue

        candidates.sort(
            key=lambda item: (
                item[0],
                item[1],
                item[2]["entry_dt"],
            )
        )
        matched_trade = candidates[0][2]
        matched_paper_ids.add(str(matched_trade["id"]))
        matched.append((research_trade, matched_trade, "fuzzy_entry_shift"))

    unmatched_paper = [trade for trade in paper_trades if trade["id"] not in matched_paper_ids]
    return matched, unmatched_research, unmatched_paper


def build_matched_rows(
    matches: List[Tuple[Dict[str, object], Dict[str, object], str]],
) -> Tuple[List[Dict[str, object]], Dict[Tuple[str, str], int]]:
    """Builds output rows for matched trades plus exit-reason counts."""

    rows: List[Dict[str, object]] = []
    exit_reason_counts: Dict[Tuple[str, str], int] = {}

    for research_trade, paper_trade, match_type in matches:
        entry_time_diff_minutes = int(
            (paper_trade["entry_dt"] - research_trade["entry_dt"]).total_seconds() // 60
        )
        exit_time_diff_minutes = int(
            (paper_trade["exit_dt"] - research_trade["exit_dt"]).total_seconds() // 60
        )
        pnl_difference = float(paper_trade["pnl"]) - float(research_trade["pnl"])
        rows.append(
            {
                "entry_time": research_trade["entry_time"],
                "direction": research_trade["direction"],
                "match_type": match_type,
                "entry_time_diff_minutes": entry_time_diff_minutes,
                "exit_time_diff_minutes": exit_time_diff_minutes,
                "research_exit_reason": research_trade["exit_reason"],
                "paper_exit_reason": paper_trade["exit_reason"],
                "research_exit_time": research_trade["exit_time"],
                "paper_exit_time": paper_trade["exit_time"],
                "research_pnl": research_trade["pnl"],
                "paper_pnl": paper_trade["pnl"],
                "pnl_difference": pnl_difference,
            }
        )
        reason_key = (
            str(research_trade["exit_reason"]),
            str(paper_trade["exit_reason"]),
        )
        exit_reason_counts[reason_key] = exit_reason_counts.get(reason_key, 0) + 1

    rows.sort(key=lambda row: abs(float(row["pnl_difference"])), reverse=True)
    return rows, exit_reason_counts


def build_unmatched_rows(trades: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """Builds unmatched trade rows."""

    return [
        {
            "entry_time": trade["entry_time"],
            "direction": trade["direction"],
            "pnl": trade["pnl"],
        }
        for trade in trades
    ]


def write_fuzzy_summary(
    output_dir: Path,
    exact_count: int,
    fuzzy_count: int,
    total_count: int,
    research_only_count: int,
    paper_only_count: int,
    matched_rows: List[Dict[str, object]],
) -> None:
    """Writes a markdown summary for exact + fuzzy matching."""

    fuzzy_rows = [row for row in matched_rows if row["match_type"] == "fuzzy_entry_shift"]
    summary_lines = [
        "# Fuzzy Match Summary",
        "",
        "- exact matches: {0}".format(exact_count),
        "- fuzzy matches: {0}".format(fuzzy_count),
        "- total matched: {0}".format(total_count),
        "- remaining research only: {0}".format(research_only_count),
        "- remaining paper only: {0}".format(paper_only_count),
        "",
        "## Top 10 Fuzzy Matches By Abs PnL Difference",
        "",
    ]

    for row in sorted(fuzzy_rows, key=lambda item: abs(float(item["pnl_difference"])), reverse=True)[:10]:
        summary_lines.append(
            "- `{0}` `{1}` entry_diff={2} exit_diff={3} pnl_diff={4} research={5} paper={6}".format(
                row["entry_time"],
                row["direction"],
                row["entry_time_diff_minutes"],
                row["exit_time_diff_minutes"],
                row["pnl_difference"],
                row["research_exit_reason"],
                row["paper_exit_reason"],
            )
        )

    summary_lines.extend(
        [
            "",
            "## Conclusion",
            "",
        ]
    )

    if research_only_count + paper_only_count <= fuzzy_count:
        conclusion = "Replay looks close enough for next-stage paper trading work."
    else:
        conclusion = "Replay is improved, but remaining unmatched trades still warrant another timing-focused pass."
    summary_lines.append("- {0}".format(conclusion))

    (output_dir / "fuzzy_match_summary.md").write_text(
        "\n".join(summary_lines) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    """Runs the research vs paper trade comparison."""

    args = parse_args()
    output_dir = Path(args.output_dir)
    research_trades = load_trades(Path(args.research), "research")
    paper_trades = load_trades(Path(args.paper), "paper")

    exact_matches, remaining_research, remaining_paper = exact_match_trades(
        research_trades,
        paper_trades,
    )
    fuzzy_matches, final_research_only, final_paper_only = fuzzy_match_trades(
        remaining_research,
        remaining_paper,
    )

    all_matches = exact_matches + fuzzy_matches
    exact_count = len(exact_matches)
    fuzzy_count = len(fuzzy_matches)
    total_count = len(all_matches)

    summary_rows = [
        {
            "research_trade_count": len(research_trades),
            "paper_trade_count": len(paper_trades),
            "exact_matched_trade_count": exact_count,
            "fuzzy_matched_trade_count": fuzzy_count,
            "total_matched_trade_count": total_count,
            "research_only_count_after_fuzzy": len(final_research_only),
            "paper_only_count_after_fuzzy": len(final_paper_only),
        }
    ]
    write_csv(
        output_dir / "summary.csv",
        [
            "research_trade_count",
            "paper_trade_count",
            "exact_matched_trade_count",
            "fuzzy_matched_trade_count",
            "total_matched_trade_count",
            "research_only_count_after_fuzzy",
            "paper_only_count_after_fuzzy",
        ],
        summary_rows,
    )

    write_csv(
        output_dir / "research_only_trades.csv",
        ["entry_time", "direction", "pnl"],
        build_unmatched_rows(final_research_only),
    )
    write_csv(
        output_dir / "paper_only_trades.csv",
        ["entry_time", "direction", "pnl"],
        build_unmatched_rows(final_paper_only),
    )

    matched_rows, exit_reason_counts = build_matched_rows(all_matches)
    write_csv(
        output_dir / "matched_trade_diff.csv",
        [
            "entry_time",
            "direction",
            "match_type",
            "entry_time_diff_minutes",
            "exit_time_diff_minutes",
            "research_exit_reason",
            "paper_exit_reason",
            "research_exit_time",
            "paper_exit_time",
            "research_pnl",
            "paper_pnl",
            "pnl_difference",
        ],
        matched_rows,
    )

    exit_reason_rows = [
        {
            "research_exit_reason": reason_key[0],
            "paper_exit_reason": reason_key[1],
            "count": count,
        }
        for reason_key, count in sorted(
            exit_reason_counts.items(),
            key=lambda item: (-item[1], item[0][0], item[0][1]),
        )
    ]
    write_csv(
        output_dir / "exit_reason_comparison.csv",
        ["research_exit_reason", "paper_exit_reason", "count"],
        exit_reason_rows,
    )

    write_fuzzy_summary(
        output_dir=output_dir,
        exact_count=exact_count,
        fuzzy_count=fuzzy_count,
        total_count=total_count,
        research_only_count=len(final_research_only),
        paper_only_count=len(final_paper_only),
        matched_rows=matched_rows,
    )

    print("Comparison output directory: {0}".format(output_dir))
    print("Research trades: {0}".format(len(research_trades)))
    print("Paper trades: {0}".format(len(paper_trades)))
    print("Exact matched trades: {0}".format(exact_count))
    print("Fuzzy matched trades: {0}".format(fuzzy_count))
    print("Total matched trades: {0}".format(total_count))
    print("Research only after fuzzy: {0}".format(len(final_research_only)))
    print("Paper only after fuzzy: {0}".format(len(final_paper_only)))


if __name__ == "__main__":
    main()
