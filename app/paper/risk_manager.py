"""Risk checks for the MNQ V4 paper trading workflow."""

from __future__ import annotations

from app.config.paper_config import PaperTradingConfig
from app.paper.position_manager import PositionManager


class RiskManager:
    """Applies lightweight pre-trade checks before paper order submission."""

    def __init__(self, config: PaperTradingConfig, position_manager: PositionManager) -> None:
        """Stores configuration and position dependencies for risk evaluation."""

        self._config = config
        self._position_manager = position_manager

    def can_open_new_position(self) -> bool:
        """Returns whether a new position can be opened under current limits."""

        return len(self._position_manager.get_all_positions()) < self._config.max_positions

    def validate_order_size(self, quantity: int) -> bool:
        """Performs a minimal order-size validation check."""

        return quantity > 0
