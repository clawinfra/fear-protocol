"""Abstract exchange adapter interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal

from fear_protocol.core.models import Balance, MarketPrice, OrderResult


class AbstractExchangeAdapter(ABC):
    """
    Exchange adapter interface. All exchanges must implement this.

    Implementations:
    - HyperliquidAdapter  (UBTC/USDC spot)
    - BinanceAdapter      (BTC/USDT spot)
    - MockAdapter         (deterministic testing)
    - PaperAdapter        (local state, no API calls)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable exchange name."""

    @property
    @abstractmethod
    def base_asset(self) -> str:
        """Base asset symbol, e.g. 'BTC', 'UBTC'."""

    @property
    @abstractmethod
    def quote_asset(self) -> str:
        """Quote asset symbol, e.g. 'USDC', 'USDT'."""

    @abstractmethod
    def get_price(self) -> MarketPrice:
        """Get current market price for the trading pair."""

    @abstractmethod
    def get_balances(self) -> dict[str, Balance]:
        """Get current balances for all relevant assets."""

    @abstractmethod
    def market_buy(self, quote_amount: Decimal) -> OrderResult:
        """
        Buy base asset using quote_amount of quote asset.

        Args:
            quote_amount: USD/USDC/USDT amount to spend.

        Returns:
            OrderResult with fill details.
        """

    @abstractmethod
    def market_sell(self, base_amount: Decimal) -> OrderResult:
        """
        Sell base_amount of base asset.

        Args:
            base_amount: Amount of base asset (BTC) to sell.

        Returns:
            OrderResult with fill details.
        """

    def validate_order_size(self, quote_amount: Decimal) -> None:
        """Validate order size meets exchange minimums. Override in subclasses."""
        pass

    def close(self) -> None:
        """Clean up connections. Override if needed."""
        pass
