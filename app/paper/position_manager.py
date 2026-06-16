"""Position tracking helpers for the MNQ V4 paper trading runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class ManagedPosition:
    """Represents an internal position record with excursion tracking."""

    symbol: str
    side: str
    quantity: int
    entry_price: float
    entry_time: datetime
    mfe_points: float = 0.0
    mae_points: float = 0.0
    metadata: Dict[str, str] = field(default_factory=dict)


class PositionManager:
    """Maintains open positions and updates derived state such as MFE and MAE."""

    def __init__(self) -> None:
        """Initializes an empty position registry."""

        self._positions: Dict[str, ManagedPosition] = {}

    def register_position(self, position: ManagedPosition) -> None:
        """Registers or replaces an open position for a symbol."""

        self._positions[position.symbol] = position

    def remove_position(self, symbol: str) -> Optional[ManagedPosition]:
        """Removes and returns a tracked position if one exists."""

        return self._positions.pop(symbol, None)

    def get_position(self, symbol: str) -> Optional[ManagedPosition]:
        """Returns the current tracked position for a symbol."""

        return self._positions.get(symbol)

    def get_all_positions(self) -> List[ManagedPosition]:
        """Returns every tracked open position."""

        return list(self._positions.values())

    def update_mfe(self, symbol: str, favorable_move_points: float) -> None:
        """Updates maximum favorable excursion for a tracked position."""

        position = self._positions.get(symbol)
        if position is None:
            return
        position.mfe_points = max(position.mfe_points, favorable_move_points)

    def update_mae(self, symbol: str, adverse_move_points: float) -> None:
        """Updates maximum adverse excursion for a tracked position."""

        position = self._positions.get(symbol)
        if position is None:
            return
        position.mae_points = max(position.mae_points, adverse_move_points)
