"""Abstract data provider interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal


class AbstractDataProvider(ABC):
    """Base class for all data providers."""

    @abstractmethod
    def get_current_fear_greed(self) -> dict[str, int | str]:
        """
        Get current Fear & Greed index.

        Returns:
            Dict with 'value' (int), 'label' (str), 'timestamp' (str).
        """

    @abstractmethod
    def get_current_price(self, symbol: str = "BTCUSDT") -> Decimal:
        """
        Get current price for a symbol.

        Args:
            symbol: Trading pair symbol.

        Returns:
            Current price as Decimal.
        """
