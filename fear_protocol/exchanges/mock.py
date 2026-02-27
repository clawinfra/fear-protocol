"""Deterministic mock exchange adapter for testing and backtesting."""
from __future__ import annotations

import uuid
from decimal import Decimal

from fear_protocol.core.models import Balance, MarketPrice, OrderResult
from fear_protocol.exchanges.base import AbstractExchangeAdapter


class MockAdapter(AbstractExchangeAdapter):
    """
    Deterministic mock exchange for testing and backtesting.

    Simulates slippage, fees, and order fills with configurable parameters.
    Maintains internal balance state to track fills.
    """

    @property
    def name(self) -> str:
        """Exchange name."""
        return "mock"

    @property
    def base_asset(self) -> str:
        """Base asset symbol."""
        return self._base_asset

    @property
    def quote_asset(self) -> str:
        """Quote asset symbol."""
        return self._quote_asset

    def __init__(
        self,
        initial_price: Decimal = Decimal("50000"),
        fee_rate: Decimal = Decimal("0.001"),
        slippage_rate: Decimal = Decimal("0.001"),
        initial_quote_balance: Decimal = Decimal("10000"),
        initial_base_balance: Decimal = Decimal("0"),
        base_asset: str = "BTC",
        quote_asset: str = "USDT",
    ) -> None:
        """
        Initialize the mock adapter.

        Args:
            initial_price: Starting price for the mock market.
            fee_rate: Fee rate applied to each trade (e.g., 0.001 = 0.1%).
            slippage_rate: Slippage applied to fills (e.g., 0.001 = 0.1%).
            initial_quote_balance: Starting quote currency balance.
            initial_base_balance: Starting base currency balance.
            base_asset: Base asset name (e.g., 'BTC').
            quote_asset: Quote asset name (e.g., 'USDT').
        """
        self._price = initial_price
        self.fee_rate = fee_rate
        self.slippage_rate = slippage_rate
        self._base_asset = base_asset
        self._quote_asset = quote_asset
        self._quote_balance = initial_quote_balance
        self._base_balance = initial_base_balance

    def set_price(self, price: Decimal) -> None:
        """Update the current mock price (called by backtest engine)."""
        self._price = price

    def get_price(self) -> MarketPrice:
        """Return mock market price with synthetic bid/ask spread."""
        spread = self._price * Decimal("0.0005")
        return MarketPrice(
            symbol=f"{self._base_asset}/{self._quote_asset}",
            bid=self._price - spread,
            ask=self._price + spread,
            last=self._price,
        )

    def get_balances(self) -> dict[str, Balance]:
        """Return current mock balances."""
        return {
            self._quote_asset: Balance(
                asset=self._quote_asset,
                free=self._quote_balance,
                locked=Decimal("0"),
            ),
            self._base_asset: Balance(
                asset=self._base_asset,
                free=self._base_balance,
                locked=Decimal("0"),
            ),
        }

    def market_buy(self, quote_amount: Decimal) -> OrderResult:
        """
        Simulate a market buy order.

        Args:
            quote_amount: Amount of quote currency to spend.

        Returns:
            OrderResult with simulated fill details.

        Raises:
            ValueError: If insufficient quote balance.
        """
        if quote_amount > self._quote_balance:
            return OrderResult(
                order_id=str(uuid.uuid4()),
                status="failed",
                filled_qty=Decimal("0"),
                avg_fill_price=Decimal("0"),
                fee=Decimal("0"),
                raw={"error": "Insufficient balance"},
            )

        # Apply slippage (buy at slightly higher price)
        fill_price = self._price * (1 + self.slippage_rate)
        fee = quote_amount * self.fee_rate
        net_quote = quote_amount - fee
        filled_qty = net_quote / fill_price

        self._quote_balance -= quote_amount
        self._base_balance += filled_qty

        return OrderResult(
            order_id=str(uuid.uuid4()),
            status="filled",
            filled_qty=filled_qty,
            avg_fill_price=fill_price,
            fee=fee,
            raw={"mock": True},
        )

    def market_sell(self, base_amount: Decimal) -> OrderResult:
        """
        Simulate a market sell order.

        Args:
            base_amount: Amount of base currency to sell.

        Returns:
            OrderResult with simulated fill details.

        Raises:
            ValueError: If insufficient base balance.
        """
        if base_amount > self._base_balance:
            return OrderResult(
                order_id=str(uuid.uuid4()),
                status="failed",
                filled_qty=Decimal("0"),
                avg_fill_price=Decimal("0"),
                fee=Decimal("0"),
                raw={"error": "Insufficient balance"},
            )

        # Apply slippage (sell at slightly lower price)
        fill_price = self._price * (1 - self.slippage_rate)
        gross_quote = base_amount * fill_price
        fee = gross_quote * self.fee_rate
        net_quote = gross_quote - fee

        self._base_balance -= base_amount
        self._quote_balance += net_quote

        return OrderResult(
            order_id=str(uuid.uuid4()),
            status="filled",
            filled_qty=base_amount,
            avg_fill_price=fill_price,
            fee=fee,
            raw={"mock": True},
        )
