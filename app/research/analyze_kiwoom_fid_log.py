"""Analyze Kiwoom FID discovery logs and rank candidate realtime fields."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional


def parse_args() -> argparse.Namespace:
    """Parses CLI arguments for the Kiwoom FID log analyzer."""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=str,
        default="data/live/kiwoom_fid_discovery.csv",
        help="Input Kiwoom FID discovery CSV path.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="reports/kiwoom_fid_analysis",
        help="Directory for analysis output files.",
    )
    return parser.parse_args()


def main() -> int:
    """Runs the Kiwoom FID log analyzer."""

    args = parse_args()
    project_root = Path(__file__).resolve().parents[2]
    input_path = resolve_path(project_root, args.input)
    output_dir = resolve_path(project_root, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        print("Kiwoom FID analyzer input not found: {0}".format(input_path))
        write_missing_summary(output_dir=output_dir, input_path=input_path)
        return 0

    events = load_events(input_path)
    field_rows = build_field_rows(events)
    write_csv(output_dir / "fid_summary.csv", field_rows)

    time_candidates = select_time_candidates(field_rows)
    price_candidates = select_price_candidates(field_rows)
    volume_candidates = select_volume_candidates(field_rows)

    write_csv(output_dir / "candidate_time_fields.csv", time_candidates)
    write_csv(output_dir / "candidate_price_fields.csv", price_candidates)
    write_csv(output_dir / "candidate_volume_fields.csv", volume_candidates)
    write_summary_markdown(
        output_dir=output_dir,
        input_path=input_path,
        field_rows=field_rows,
        time_candidates=time_candidates,
        price_candidates=price_candidates,
        volume_candidates=volume_candidates,
    )

    print("Kiwoom FID analysis completed")
    print("Input: {0}".format(input_path))
    print("Output dir: {0}".format(output_dir))
    print("Fields analyzed: {0}".format(len(field_rows)))
    print("Time candidates: {0}".format(len(time_candidates)))
    print("Price candidates: {0}".format(len(price_candidates)))
    print("Volume candidates: {0}".format(len(volume_candidates)))
    return 0


def resolve_path(project_root: Path, raw_path: str) -> Path:
    """Resolves a CLI path relative to the project root when needed."""

    path = Path(raw_path)
    if path.is_absolute():
        return path
    return project_root / path


def load_events(input_path: Path) -> List[Dict[str, object]]:
    """Loads discovery events and parses their embedded FID JSON payload."""

    events = []  # type: List[Dict[str, object]]
    with input_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            fid_values = parse_fid_values(row.get("fid_values_json", ""))
            events.append(
                {
                    "received_at": row.get("received_at", ""),
                    "code": row.get("code", ""),
                    "real_type": row.get("real_type", ""),
                    "fid_values": fid_values,
                }
            )
    return events


def parse_fid_values(raw_json: str) -> Dict[str, object]:
    """Parses a single FID JSON blob into a dictionary."""

    try:
        parsed = json.loads(raw_json or "{}")
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return parsed


def build_field_rows(events: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """Builds summary statistics for every observed FID key."""

    ordered_keys = []  # type: List[str]
    seen_keys = set()
    for event in events:
        fid_values = event.get("fid_values", {})
        if not isinstance(fid_values, dict):
            continue
        for key in fid_values:
            normalized_key = str(key)
            if normalized_key in seen_keys:
                continue
            seen_keys.add(normalized_key)
            ordered_keys.append(normalized_key)

    rows = []  # type: List[Dict[str, object]]
    for key in ordered_keys:
        values = [extract_string_value(event, key) for event in events]
        rows.append(build_field_stats(key, values))
    rows.sort(key=lambda row: str(row["key"]))
    return rows


def extract_string_value(event: Dict[str, object], key: str) -> str:
    """Returns one event's string value for the requested FID key."""

    fid_values = event.get("fid_values", {})
    if not isinstance(fid_values, dict):
        return ""
    value = fid_values.get(key, "")
    if value is None:
        return ""
    return str(value).strip()


def build_field_stats(key: str, values: List[str]) -> Dict[str, object]:
    """Computes summary statistics for one candidate field."""

    total_count = len(values)
    non_empty_values = [value for value in values if value != ""]
    unique_values = list(dict.fromkeys(non_empty_values))
    numeric_values = [parsed for parsed in (parse_numeric(value) for value in non_empty_values) if parsed is not None]
    changed_count = compute_changed_count(non_empty_values)
    monotonic_like_score = compute_monotonic_like_score(numeric_values)

    return {
        "key": key,
        "count": total_count,
        "non_empty_count": len(non_empty_values),
        "unique_count": len(set(non_empty_values)),
        "sample_values": " | ".join(unique_values[:5]),
        "numeric_parse_rate": format_ratio(len(numeric_values), len(non_empty_values)),
        "min_numeric": format_optional_number(min(numeric_values) if numeric_values else None),
        "max_numeric": format_optional_number(max(numeric_values) if numeric_values else None),
        "avg_numeric": format_optional_number(
            sum(numeric_values) / len(numeric_values) if numeric_values else None
        ),
        "monotonic_like_score": format_optional_number(monotonic_like_score),
        "changed_count": changed_count,
    }


def compute_changed_count(values: List[str]) -> int:
    """Counts how often consecutive non-empty values changed."""

    if not values:
        return 0
    changed_count = 0
    previous = values[0]
    for value in values[1:]:
        if value != previous:
            changed_count += 1
        previous = value
    return changed_count


def compute_monotonic_like_score(values: List[float]) -> Optional[float]:
    """Scores how often a numeric sequence moves monotonically between observations."""

    if len(values) < 2:
        return None
    monotonic_steps = 0
    comparable_steps = 0
    previous = values[0]
    direction = 0
    for value in values[1:]:
        delta = value - previous
        if delta != 0:
            current_direction = 1 if delta > 0 else -1
            comparable_steps += 1
            if direction == 0 or current_direction == direction:
                monotonic_steps += 1
            direction = current_direction
        previous = value
    if comparable_steps == 0:
        return 1.0
    return monotonic_steps / comparable_steps


def parse_numeric(value: str) -> Optional[float]:
    """Parses numeric-looking FID values."""

    normalized = value.replace(",", "").strip()
    if normalized.startswith("+"):
        normalized = normalized[1:]
    if not normalized:
        return None
    try:
        return float(normalized)
    except ValueError:
        return None


def format_ratio(numerator: int, denominator: int) -> str:
    """Formats a simple ratio as a decimal string."""

    if denominator <= 0:
        return "0.0000"
    return "{0:.4f}".format(numerator / denominator)


def format_optional_number(value: Optional[float]) -> str:
    """Formats optional numeric values consistently for CSV output."""

    if value is None:
        return ""
    return "{0:.6f}".format(value)


def select_time_candidates(field_rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """Ranks candidate time-like fields."""

    candidates = []  # type: List[Dict[str, object]]
    for row in field_rows:
        sample_values = split_sample_values(str(row["sample_values"]))
        time_like_count = sum(1 for value in sample_values if looks_like_time(value))
        key_name = str(row["key"]).lower()
        if time_like_count > 0 or "time" in key_name:
            candidate = dict(row)
            candidate["reason"] = build_reason(
                [
                    "key contains time" if "time" in key_name else "",
                    "sample values look like HHMMSS" if time_like_count > 0 else "",
                ]
            )
            candidates.append(candidate)
    candidates.sort(key=lambda row: (-int(row["non_empty_count"]), str(row["key"])))
    return candidates


def select_price_candidates(field_rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """Ranks candidate price-like fields."""

    candidates = []  # type: List[Dict[str, object]]
    for row in field_rows:
        numeric_rate = float(row["numeric_parse_rate"] or 0.0)
        min_numeric = parse_numeric(str(row["min_numeric"]))
        max_numeric = parse_numeric(str(row["max_numeric"]))
        changed_count = int(row["changed_count"])
        key_name = str(row["key"]).lower()
        in_price_range = (
            min_numeric is not None
            and max_numeric is not None
            and min_numeric >= 1000
            and max_numeric <= 100000
        )
        if numeric_rate >= 0.8 and in_price_range and changed_count > 0:
            candidate = dict(row)
            candidate["reason"] = build_reason(
                [
                    "numeric parse rate is high",
                    "values fall within broad MNQ-like price range",
                    "value changes across events" if changed_count > 0 else "",
                    "key contains price" if "price" in key_name else "",
                ]
            )
            candidates.append(candidate)
    candidates.sort(
        key=lambda row: (-int(row["changed_count"]), -int(row["non_empty_count"]), str(row["key"]))
    )
    return candidates


def select_volume_candidates(field_rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """Ranks candidate volume-like fields."""

    candidates = []  # type: List[Dict[str, object]]
    for row in field_rows:
        numeric_rate = float(row["numeric_parse_rate"] or 0.0)
        min_numeric = parse_numeric(str(row["min_numeric"]))
        avg_numeric = parse_numeric(str(row["avg_numeric"]))
        key_name = str(row["key"]).lower()
        volume_name_hint = any(token in key_name for token in ("volume", "qty", "contract", "체결량"))
        non_negative = min_numeric is not None and min_numeric >= 0
        small_integer_like = avg_numeric is not None and avg_numeric <= 100000
        if (volume_name_hint or str(row["key"]) in {"15"}) and numeric_rate >= 0.8 and non_negative and small_integer_like:
            candidate = dict(row)
            candidate["reason"] = build_reason(
                [
                    "key name looks volume-like" if volume_name_hint else "",
                    "placeholder FID 15 often maps to volume-like fields" if str(row["key"]) == "15" else "",
                    "numeric and non-negative",
                ]
            )
            candidates.append(candidate)
    candidates.sort(
        key=lambda row: (-int(row["non_empty_count"]), -int(row["changed_count"]), str(row["key"]))
    )
    return candidates


def split_sample_values(sample_values: str) -> List[str]:
    """Splits the stored sample value string back into individual examples."""

    if not sample_values:
        return []
    return [value.strip() for value in sample_values.split("|") if value.strip()]


def looks_like_time(value: str) -> bool:
    """Returns whether a value resembles HHMMSS or HH:MM:SS."""

    stripped = value.strip()
    digits_only = stripped.replace(":", "")
    return len(digits_only) == 6 and digits_only.isdigit()


def build_reason(parts: Iterable[str]) -> str:
    """Builds a compact human-readable reason string."""

    filtered = [part for part in parts if part]
    return "; ".join(filtered)


def write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    """Writes a list of dict rows to CSV."""

    fieldnames = [
        "key",
        "count",
        "non_empty_count",
        "unique_count",
        "sample_values",
        "numeric_parse_rate",
        "min_numeric",
        "max_numeric",
        "avg_numeric",
        "monotonic_like_score",
        "changed_count",
        "reason",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            output_row = {name: row.get(name, "") for name in fieldnames}
            writer.writerow(output_row)


def write_summary_markdown(
    output_dir: Path,
    input_path: Path,
    field_rows: List[Dict[str, object]],
    time_candidates: List[Dict[str, object]],
    price_candidates: List[Dict[str, object]],
    volume_candidates: List[Dict[str, object]],
) -> None:
    """Writes a markdown overview of the analysis outputs."""

    lines = [
        "# Kiwoom FID Analysis Summary",
        "",
        "Input: `{0}`".format(input_path),
        "",
        "## Overview",
        "",
        "- Fields analyzed: `{0}`".format(len(field_rows)),
        "- Time candidates: `{0}`".format(len(time_candidates)),
        "- Price candidates: `{0}`".format(len(price_candidates)),
        "- Volume candidates: `{0}`".format(len(volume_candidates)),
        "",
        "## Inspect First",
        "",
        "- `candidate_time_fields.csv`",
        "- `candidate_price_fields.csv`",
        "- `candidate_volume_fields.csv`",
        "- `fid_summary.csv`",
        "",
        "## Top Candidates",
        "",
    ]
    lines.extend(build_candidate_lines("Time", time_candidates))
    lines.extend(build_candidate_lines("Price", price_candidates))
    lines.extend(build_candidate_lines("Volume", volume_candidates))
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_candidate_lines(title: str, rows: List[Dict[str, object]]) -> List[str]:
    """Builds markdown lines for one candidate category."""

    lines = ["### {0}".format(title), ""]
    if not rows:
        lines.append("- No strong candidates detected.")
        lines.append("")
        return lines
    for row in rows[:5]:
        lines.append(
            "- `{0}` non_empty=`{1}` changed=`{2}` samples=`{3}` reason=`{4}`".format(
                row.get("key", ""),
                row.get("non_empty_count", ""),
                row.get("changed_count", ""),
                row.get("sample_values", ""),
                row.get("reason", ""),
            )
        )
    lines.append("")
    return lines


def write_missing_summary(output_dir: Path, input_path: Path) -> None:
    """Writes a markdown note when the requested input file is missing."""

    lines = [
        "# Kiwoom FID Analysis Summary",
        "",
        "Input file not found: `{0}`".format(input_path),
        "",
        "No analysis was performed because the FID discovery CSV does not exist yet.",
        "",
        "Run FID discovery first, then rerun this analyzer.",
    ]
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
