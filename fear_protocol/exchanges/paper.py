"""Paper trading adapter — real prices, simulated fills, local state."""
from __future__ import annotations

import json
import uuid
from decimal import Decimal
from pathlib import Path

import requests

from fear_protocol.core.models import Balance, MarketPrice, OrderResult
from fear_protocol.exchanges.base import AbstractExchangeAdapter


class PaperAdapter(AbstractExchangeAdapter):
    """
    Paper trading adapter.

    Fetches real market prices but doesn't place orders.
    Tracks positions in a local state file.
    """

    @property
    def name(self) -> str:
        """Exchange name."""
        return "paper"

    @property
    def base_asset(self) -> str:
        """Base asset symbol."""
        return "BTC"

    @property
    def quote_asset(self) -> str:
        """Quote asset symbol."""
        return "USDT"

    def __init__(
        self,
        initial_quote: Decimal = Decimal("10000"),
        fee_rate: Decimal = Decimal("0.001"),
        state_file: Path | None = None,
    ) -> None:
        """
        Initialize the paper adapter.

        Args:
            initial_quote: Starting quote balance (USDT).
            fee_rate: Simulated fee rate.
            state_file: Optional path to persist paper trading state.
        """
        self.fee_rate = fee_rate
        self.state_file = state_file
        self._state = self._load_state(initial_quote)

    def _load_state(self, initial_quote: Decimal) -> dict:
        if self.state_file and self.state_file.exists():
            data = json.loads(self.state_file.read_text())
            return data
        return {
            "quote_balance": str(initial_quote),
            "base_balance": "0",
        }

    def _save_state(self) -> None:
        if self.state_file:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            self.state_file.write_text(json.dumps(self._state, indent=2))

    def get_price(self) -> MarketPrice:
        """Fetch real BTC/USDT price from Binance."""
        resp = requests.get(
            "https://api.binance.com/api/v3/ticker/bookTicker",
            params={"symbol": "BTCUSDT"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        bid = Decimal(data["bidPrice"])
        ask = Decimal(data["askPrice"])
        last = (bid + ask) / 2
        return MarketPrice(symbol="BTC/USDT", bid=bid, ask=ask, last=last)

    def get_balances(self) -> dict[str, Balance]:
        """Return current paper balances."""
        return {
            "USDT": Balance(
                asset="USDT",
                free=Decimal(self._state["quote_balance"]),
                locked=Decimal("0"),
            ),
            "BTC": Balance(
                asset="BTC",
                free=Decimal(self._state["base_balance"]),
                locked=Decimal("0"),
            ),
        }

    def market_buy(self, quote_amount: Decimal) -> OrderResult:
        """Simulate a market buy at current price."""
        quote_bal = Decimal(self._state["quote_balance"])
        if quote_amount > quote_bal:
            return OrderResult(
                order_id=str(uuid.uuid4()),
                status="failed",
                filled_qty=Decimal("0"),
                avg_fill_price=Decimal("0"),
                fee=Decimal("0"),
                raw={"error": "Insufficient paper balance"},
            )
        price_data = self.get_price()
        fill_price = price_data.ask  # buy at ask
        fee = quote_amount * self.fee_rate
        net_quote = quote_amount - fee
        filled_qty = (net_quote / fill_price).quantize(Decimal("0.00001"))

        self._state["quote_balance"] = str(quote_bal - quote_amount)
        self._state["base_balance"] = str(
            Decimal(self._state["base_balance"]) + filled_qty
        )
        self._save_state()

        return OrderResult(
            order_id=str(uuid.uuid4()),
            status="filled",
            filled_qty=filled_qty,
            avg_fill_price=fill_price,
            fee=fee,
            raw={"paper": True},
        )

    def market_sell(self, base_amount: Decimal) -> OrderResult:
        """Simulate a market sell at current price."""
        base_bal = Decimal(self._state["base_balance"])
        if base_amount > base_bal:
            return OrderResult(
                order_id=str(uuid.uuid4()),
                status="failed",
                filled_qty=Decimal("0"),
                avg_fill_price=Decimal("0"),
                fee=Decimal("0"),
                raw={"error": "Insufficient paper balance"},
            )
        price_data = self.get_price()
        fill_price = price_data.bid  # sell at bid
        gross_quote = base_amount * fill_price
        fee = gross_quote * self.fee_rate
        net_quote = gross_quote - fee

        self._state["base_balance"] = str(base_bal - base_amount)
        self._state["quote_balance"] = str(
            Decimal(self._state["quote_balance"]) + net_quote
        )
        self._save_state()

        return OrderResult(
            order_id=str(uuid.uuid4()),
            status="filled",
            filled_qty=base_amount,
            avg_fill_price=fill_price,
            fee=fee,
            raw={"paper": True},
        )
