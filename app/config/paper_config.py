"""Configuration objects for the MNQ V4 paper trading runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PaperTradingConfig:
    """Stores configurable paths and runtime settings for paper trading."""

    project_root: Path
    symbol: str = "MNQ"
    timeframe_minutes: int = 15
    starting_balance: float = 100_000.0
    max_positions: int = 1
    log_dir: Path = field(init=False)
    paper_data_dir: Path = field(init=False)
    report_dir: Path = field(init=False)

    def __post_init__(self) -> None:
        """Derives standard runtime directories from the project root."""

        self.log_dir = self.project_root / "logs"
        self.paper_data_dir = self.project_root / "data" / "paper"
        self.report_dir = self.project_root / "reports"

