"""Generate a concise paper trading performance report from trades.csv."""

from __future__ import annotations

import argparse
import csv
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List


def parse_args() -> argparse.Namespace:
    """Parses CLI arguments for standalone report generation."""

    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--trades",
        default=str(project_root / "data" / "paper" / "trades.csv"),
        help="Path to paper trades.csv",
    )
    parser.add_argument(
        "--output-dir",
        default=str(project_root / "reports" / "paper_performance"),
        help="Output directory for generated report files",
    )
    return parser.parse_args()


def load_trades(path: Path) -> List[Dict[str, object]]:
    """Loads paper trades into normalized dictionaries."""

    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    trades: List[Dict[str, object]] = []
    for row in rows:
        exit_time = str(row.get("exit_time", "")).strip()
        side = str(row.get("side", "")).strip().lower()
        trades.append(
            {
                "symbol": str(row.get("symbol", "")).strip(),
                "side": side,
                "qty": int(row.get("qty", "0") or 0),
                "entry_time": str(row.get("entry_time", "")).strip(),
                "exit_time": exit_time,
                "exit_dt": datetime.fromisoformat(exit_time),
                "entry_price": float(row.get("entry_price", "0") or 0.0),
                "exit_price": float(row.get("exit_price", "0") or 0.0),
                "entry_reason": str(row.get("entry_reason", "")).strip(),
                "exit_reason": str(row.get("exit_reason", "")).strip(),
                "pnl_points": float(row.get("pnl_points", "0") or 0.0),
                "pnl_usd": float(row.get("pnl_usd", "0") or 0.0),
                "mfe": float(row.get("mfe", "0") or 0.0),
                "mae": float(row.get("mae", "0") or 0.0),
            }
        )
    trades.sort(key=lambda trade: trade["exit_dt"])
    return trades


def write_csv(path: Path, fieldnames: List[str], rows: List[Dict[str, object]]) -> None:
    """Writes CSV rows."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def safe_profit_factor(gross_profit: float, gross_loss: float) -> float:
    """Returns profit factor with zero-loss protection."""

    if gross_loss == 0:
        return 0.0 if gross_profit == 0 else float("inf")
    return gross_profit / abs(gross_loss)


def build_equity_curve(trades: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """Builds an exit-time ordered equity curve."""

    cumulative_pnl = 0.0
    peak_equity = 0.0
    curve_rows: List[Dict[str, object]] = []
    for trade in trades:
        cumulative_pnl += float(trade["pnl_usd"])
        peak_equity = max(peak_equity, cumulative_pnl)
        drawdown_usd = cumulative_pnl - peak_equity
        curve_rows.append(
            {
                "exit_time": trade["exit_time"],
                "pnl_usd": trade["pnl_usd"],
                "cumulative_pnl_usd": cumulative_pnl,
                "drawdown_usd": drawdown_usd,
            }
        )
    return curve_rows


def generate_report(trades_path: Path, output_dir: Path) -> Dict[str, object]:
    """Generates all report artifacts and returns key summary metrics."""

    trades = load_trades(trades_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    pnl_usd_values = [float(trade["pnl_usd"]) for trade in trades]
    pnl_points_values = [float(trade["pnl_points"]) for trade in trades]
    closed_trades = len(trades)
    total_pnl_usd = sum(pnl_usd_values)
    total_pnl_points = sum(pnl_points_values)
    average_pnl_usd = statistics.mean(pnl_usd_values) if pnl_usd_values else 0.0
    median_pnl_usd = statistics.median(pnl_usd_values) if pnl_usd_values else 0.0
    win_count = sum(1 for value in pnl_usd_values if value > 0)
    loss_count = sum(1 for value in pnl_usd_values if value < 0)
    win_rate = (win_count / closed_trades) if closed_trades else 0.0
    gross_profit = sum(value for value in pnl_usd_values if value > 0)
    gross_loss = sum(value for value in pnl_usd_values if value < 0)
    profit_factor = safe_profit_factor(gross_profit, gross_loss)
    long_trade_count = sum(1 for trade in trades if str(trade["side"]) == "long")
    short_trade_count = sum(1 for trade in trades if str(trade["side"]) == "short")
    long_pnl_usd = sum(float(trade["pnl_usd"]) for trade in trades if str(trade["side"]) == "long")
    short_pnl_usd = sum(float(trade["pnl_usd"]) for trade in trades if str(trade["side"]) == "short")

    equity_curve_rows = build_equity_curve(trades)
    max_drawdown_usd = min((float(row["drawdown_usd"]) for row in equity_curve_rows), default=0.0)

    summary = {
        "closed_trades": closed_trades,
        "total_pnl_usd": total_pnl_usd,
        "total_pnl_points": total_pnl_points,
        "average_pnl_usd": average_pnl_usd,
        "median_pnl_usd": median_pnl_usd,
        "win_count": win_count,
        "loss_count": loss_count,
        "win_rate": win_rate,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": profit_factor,
        "max_drawdown_usd": max_drawdown_usd,
        "long_trade_count": long_trade_count,
        "short_trade_count": short_trade_count,
        "long_pnl_usd": long_pnl_usd,
        "short_pnl_usd": short_pnl_usd,
    }

    write_csv(output_dir / "summary.csv", list(summary.keys()), [summary])

    trades_by_year: Dict[str, Dict[str, object]] = defaultdict(
        lambda: {"year": "", "trade_count": 0, "pnl_usd": 0.0, "pnl_points": 0.0}
    )
    for trade in trades:
        year = str(trade["exit_dt"].year)
        row = trades_by_year[year]
        row["year"] = year
        row["trade_count"] = int(row["trade_count"]) + 1
        row["pnl_usd"] = float(row["pnl_usd"]) + float(trade["pnl_usd"])
        row["pnl_points"] = float(row["pnl_points"]) + float(trade["pnl_points"])
    write_csv(
        output_dir / "trades_by_year.csv",
        ["year", "trade_count", "pnl_usd", "pnl_points"],
        sorted(trades_by_year.values(), key=lambda row: row["year"]),
    )

    trades_by_side: Dict[str, Dict[str, object]] = defaultdict(
        lambda: {"side": "", "trade_count": 0, "pnl_usd": 0.0, "pnl_points": 0.0}
    )
    for trade in trades:
        side = str(trade["side"])
        row = trades_by_side[side]
        row["side"] = side
        row["trade_count"] = int(row["trade_count"]) + 1
        row["pnl_usd"] = float(row["pnl_usd"]) + float(trade["pnl_usd"])
        row["pnl_points"] = float(row["pnl_points"]) + float(trade["pnl_points"])
    write_csv(
        output_dir / "trades_by_side.csv",
        ["side", "trade_count", "pnl_usd", "pnl_points"],
        sorted(trades_by_side.values(), key=lambda row: row["side"]),
    )

    exit_reason_summary: Dict[str, Dict[str, object]] = defaultdict(
        lambda: {"exit_reason": "", "trade_count": 0, "pnl_usd": 0.0}
    )
    for trade in trades:
        exit_reason = str(trade["exit_reason"])
        row = exit_reason_summary[exit_reason]
        row["exit_reason"] = exit_reason
        row["trade_count"] = int(row["trade_count"]) + 1
        row["pnl_usd"] = float(row["pnl_usd"]) + float(trade["pnl_usd"])
    write_csv(
        output_dir / "exit_reason_summary.csv",
        ["exit_reason", "trade_count", "pnl_usd"],
        sorted(exit_reason_summary.values(), key=lambda row: (-int(row["trade_count"]), row["exit_reason"])),
    )

    write_csv(
        output_dir / "equity_curve.csv",
        ["exit_time", "pnl_usd", "cumulative_pnl_usd", "drawdown_usd"],
        equity_curve_rows,
    )

    summary_lines = [
        "# Paper Performance Summary",
        "",
        "- closed_trades: {0}".format(closed_trades),
        "- total_pnl_usd: {0}".format(total_pnl_usd),
        "- total_pnl_points: {0}".format(total_pnl_points),
        "- average_pnl_usd: {0}".format(average_pnl_usd),
        "- median_pnl_usd: {0}".format(median_pnl_usd),
        "- win_count: {0}".format(win_count),
        "- loss_count: {0}".format(loss_count),
        "- win_rate: {0}".format(win_rate),
        "- gross_profit: {0}".format(gross_profit),
        "- gross_loss: {0}".format(gross_loss),
        "- profit_factor: {0}".format(profit_factor),
        "- max_drawdown_usd: {0}".format(max_drawdown_usd),
        "- long_trade_count: {0}".format(long_trade_count),
        "- short_trade_count: {0}".format(short_trade_count),
        "- long_pnl_usd: {0}".format(long_pnl_usd),
        "- short_pnl_usd: {0}".format(short_pnl_usd),
    ]
    (output_dir / "summary.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    summary["report_path"] = str(output_dir)
    return summary


def main() -> None:
    """Runs standalone report generation."""

    args = parse_args()
    summary = generate_report(Path(args.trades), Path(args.output_dir))
    print("Report path: {0}".format(summary["report_path"]))
    print("Closed trades: {0}".format(summary["closed_trades"]))
    print("Total PnL USD: {0}".format(summary["total_pnl_usd"]))
    print("Win rate: {0}".format(summary["win_rate"]))
    print("Profit factor: {0}".format(summary["profit_factor"]))
    print("Max drawdown USD: {0}".format(summary["max_drawdown_usd"]))


if __name__ == "__main__":
    main()
