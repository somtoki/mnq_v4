"""Broker interfaces shared by paper and future live trading adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class OrderRequest:
    """Represents a broker order request in a transport-agnostic format."""

    symbol: str
    side: str
    quantity: int
    order_type: str = "market"
    price: Optional[float] = None
    strategy_tag: Optional[str] = None


@dataclass
class OrderResult:
    """Represents the normalized result returned by a broker adapter."""

    order_id: str
    symbol: str
    side: str
    quantity: int
    filled_price: Optional[float]
    status: str
    timestamp: datetime
    metadata: Dict[str, Any]


@dataclass
class BrokerPosition:
    """Represents an open broker position snapshot."""

    symbol: str
    quantity: int
    side: str
    average_price: float
    opened_at: datetime


class BrokerInterface(ABC):
    """Defines the minimum broker operations required by the paper trader."""

    @abstractmethod
    def buy(self, request: OrderRequest) -> OrderResult:
        """Submits a buy order and returns a normalized result."""

    @abstractmethod
    def sell(self, request: OrderRequest) -> OrderResult:
        """Submits a sell order and returns a normalized result."""

    @abstractmethod
    def close_position(self, symbol: str) -> Optional[OrderResult]:
        """Closes an open position for the given symbol if one exists."""

    @abstractmethod
    def get_balance(self) -> float:
        """Returns the current cash balance or buying power snapshot."""

    @abstractmethod
    def get_positions(self) -> List[BrokerPosition]:
        """Returns the current open positions from the broker."""
