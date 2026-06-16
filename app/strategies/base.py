"""Strategy interfaces and signal models for the MNQ V4 project."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict


class SignalType(str, Enum):
    """Enumerates the supported strategy signal types."""

    NONE = "NONE"
    LONG_ENTRY = "LONG_ENTRY"
    SHORT_ENTRY = "SHORT_ENTRY"
    LONG_EXIT = "LONG_EXIT"
    SHORT_EXIT = "SHORT_EXIT"


@dataclass
class StrategySignal:
    """Represents a normalized strategy output that can be routed to execution."""

    signal_type: SignalType
    symbol: str
    timestamp: datetime
    price: float
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class StrategyInterface(ABC):
    """Defines the contract between bar-driven strategies and the paper runtime."""

    @abstractmethod
    def on_bar(self, bar: Any) -> StrategySignal:
        """Evaluates a completed bar and returns the next strategy signal."""

    @abstractmethod
    def get_name(self) -> str:
        """Returns a user-friendly strategy name."""

    @abstractmethod
    def reset(self) -> None:
        """Resets strategy state before a fresh run or replay."""
