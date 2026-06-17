"""Discover installed Kiwoom COM controls for overseas futures environments."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

try:
    import winreg
except ImportError:  # pragma: no cover - Windows-specific module.
    winreg = None  # type: ignore

try:
    from PyQt5.QAxContainer import QAxWidget  # type: ignore
    from PyQt5.QtWidgets import QApplication  # type: ignore
except ImportError:  # pragma: no cover - optional dependency.
    QApplication = None
    QAxWidget = None


CANDIDATE_PROG_IDS = [
    "KHOPENAPI.KHOpenAPICtrl.1",
    "KFOPENAPI.KFOpenAPICtrl.1",
    "KFOpenAPI.KFOpenAPICtrl.1",
    "KHOPENAPI.KHOpenAPICtrl",
    "KFOPENAPI.KFOpenAPICtrl",
]

METHOD_SIGNATURES = [
    "CommConnect()",
    "GetConnectState()",
    "SetRealReg(QString, QString, QString, QString)",
    "SetRealRemove(QString, QString)",
]


def main() -> int:
    """Discovers registry and QAx availability for candidate Kiwoom COM controls."""

    project_root = Path(__file__).resolve().parents[2]
    output_dir = project_root / "reports" / "kiwoom_api_discovery"
    output_dir.mkdir(parents=True, exist_ok=True)

    qax_available = QAxWidget is not None and QApplication is not None
    app = None
    if qax_available:
        app = QApplication.instance() or QApplication([])

    rows = []  # type: List[Dict[str, str]]
    for prog_id in CANDIDATE_PROG_IDS:
        rows.append(inspect_candidate(prog_id))

    write_candidates_csv(output_dir / "candidates.csv", rows)
    write_summary_md(output_dir / "summary.md", rows, qax_available)

    print("Kiwoom API discovery completed")
    print("Output dir: {0}".format(output_dir))
    print("Detected registry ProgIDs: {0}".format(", ".join(find_detected_prog_ids(rows)) or "None"))
    print("Likely overseas futures ProgID: {0}".format(select_likely_overseas_progid(rows)))

    _ = app
    return 0


def inspect_candidate(prog_id: str) -> Dict[str, str]:
    """Inspects one candidate ProgID using registry plus optional QAx metadata."""

    registry_exists = registry_key_exists(prog_id)
    control_created = False
    control_name = ""
    documentation_excerpt = ""
    method_support = {signature: "unavailable" for signature in METHOD_SIGNATURES}
    qax_error = ""

    if QAxWidget is not None and QApplication is not None:
        widget = None
        try:
            widget = QAxWidget(prog_id)
            control_created = not widget.isNull()
            if control_created:
                control_name = safe_widget_name(widget)
                documentation = safe_generate_documentation(widget)
                documentation_excerpt = documentation[:200].replace("\r", " ").replace("\n", " ").strip()
                for signature in METHOD_SIGNATURES:
                    method_support[signature] = "yes" if signature in documentation else "unknown"
            else:
                qax_error = "QAxWidget is null after creation"
        except Exception as error:
            qax_error = str(error)
        finally:
            if widget is not None:
                widget.clear()
                widget.deleteLater()
    else:
        qax_error = "PyQt5.QAxContainer is unavailable"

    return {
        "prog_id": prog_id,
        "registry_exists": format_bool(registry_exists),
        "qax_available": format_bool(QAxWidget is not None and QApplication is not None),
        "control_created": format_bool(control_created),
        "control_name": control_name,
        "commconnect_callable": method_support["CommConnect()"],
        "getconnectstate_callable": method_support["GetConnectState()"],
        "setrealreg_callable": method_support["SetRealReg(QString, QString, QString, QString)"],
        "setrealremove_callable": method_support["SetRealRemove(QString, QString)"],
        "documentation_excerpt": documentation_excerpt,
        "qax_error": qax_error,
    }


def registry_key_exists(prog_id: str) -> bool:
    """Returns whether the ProgID exists under HKEY_CLASSES_ROOT."""

    if winreg is None:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, prog_id)
    except OSError:
        return False
    winreg.CloseKey(key)
    return True


def safe_widget_name(widget: "QAxWidget") -> str:
    """Returns a readable widget/control name when available."""

    try:
        name = widget.control()
        if name:
            return str(name)
    except Exception:
        pass
    try:
        name = widget.objectName()
        if name:
            return str(name)
    except Exception:
        pass
    return ""


def safe_generate_documentation(widget: "QAxWidget") -> str:
    """Returns generated COM documentation when supported."""

    try:
        documentation = widget.generateDocumentation()
    except Exception:
        return ""
    if documentation is None:
        return ""
    return str(documentation)


def write_candidates_csv(path: Path, rows: List[Dict[str, str]]) -> None:
    """Writes candidate inspection results to CSV."""

    fieldnames = [
        "prog_id",
        "registry_exists",
        "qax_available",
        "control_created",
        "control_name",
        "commconnect_callable",
        "getconnectstate_callable",
        "setrealreg_callable",
        "setrealremove_callable",
        "documentation_excerpt",
        "qax_error",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_summary_md(path: Path, rows: List[Dict[str, str]], qax_available: bool) -> None:
    """Writes a markdown summary with the most likely overseas futures control."""

    detected_prog_ids = find_detected_prog_ids(rows)
    likely_prog_id = select_likely_overseas_progid(rows)
    lines = [
        "# Kiwoom API Discovery Summary",
        "",
        "## Environment",
        "",
        "- PyQt5.QAxContainer available: `{0}`".format(format_bool(qax_available)),
        "- Candidate ProgIDs tested: `{0}`".format(len(rows)),
        "",
        "## Detected ProgIDs",
        "",
    ]
    if detected_prog_ids:
        for prog_id in detected_prog_ids:
            lines.append("- `{0}`".format(prog_id))
    else:
        lines.append("- No candidate ProgID detected in registry or via QAx creation.")

    lines.extend(
        [
            "",
            "## Likely Overseas Futures ProgID",
            "",
            "- `{0}`".format(likely_prog_id),
            "",
            "HeroMoonG / overseas futures environments may use a different COM control from domestic stock OpenAPI.",
            "The next integration step should follow the detected overseas futures-like ProgID rather than assuming domestic compatibility.",
            "",
            "## Candidate Notes",
            "",
        ]
    )
    for row in rows:
        lines.append(
            "- `{0}` registry=`{1}` created=`{2}` CommConnect=`{3}` GetConnectState=`{4}` SetRealReg=`{5}` SetRealRemove=`{6}` error=`{7}`".format(
                row["prog_id"],
                row["registry_exists"],
                row["control_created"],
                row["commconnect_callable"],
                row["getconnectstate_callable"],
                row["setrealreg_callable"],
                row["setrealremove_callable"],
                row["qax_error"] or "",
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def find_detected_prog_ids(rows: List[Dict[str, str]]) -> List[str]:
    """Returns candidate ProgIDs detected either in registry or QAx creation."""

    detected = []  # type: List[str]
    for row in rows:
        if row["registry_exists"] == "True" or row["control_created"] == "True":
            detected.append(row["prog_id"])
    return detected


def select_likely_overseas_progid(rows: List[Dict[str, str]]) -> str:
    """Returns the most likely overseas futures ProgID from discovered candidates."""

    for preferred in ("KFOPENAPI.KFOpenAPICtrl.1", "KFOpenAPI.KFOpenAPICtrl.1", "KFOPENAPI.KFOpenAPICtrl"):
        for row in rows:
            if row["prog_id"] == preferred and (
                row["registry_exists"] == "True" or row["control_created"] == "True"
            ):
                return preferred
    for row in rows:
        if row["registry_exists"] == "True" or row["control_created"] == "True":
            return row["prog_id"]
    return "None detected"


def format_bool(value: bool) -> str:
    """Formats booleans consistently for CSV and markdown."""

    return "True" if value else "False"


if __name__ == "__main__":
    raise SystemExit(main())
