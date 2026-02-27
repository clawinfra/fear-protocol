"""Tests for the MockAdapter exchange."""
from __future__ import annotations

from decimal import Decimal

import pytest

from fear_protocol.exchanges.mock import MockAdapter


class TestMockAdapter:
    def test_name(self) -> None:
        m = MockAdapter()
        assert m.name == "mock"
        assert m.base_asset == "BTC"
        assert m.quote_asset == "USDT"

    def test_get_price(self) -> None:
        m = MockAdapter(initial_price=Decimal("50000"))
        p = m.get_price()
        assert p.last == Decimal("50000")
        assert p.bid < p.ask
        assert p.mid == Decimal("50000")

    def test_set_price(self) -> None:
        m = MockAdapter(initial_price=Decimal("50000"))
        m.set_price(Decimal("60000"))
        p = m.get_price()
        assert p.last == Decimal("60000")

    def test_get_balances(self) -> None:
        m = MockAdapter(
            initial_quote_balance=Decimal("5000"),
            initial_base_balance=Decimal("0.5"),
        )
        b = m.get_balances()
        assert b["USDT"].free == Decimal("5000")
        assert b["BTC"].free == Decimal("0.5")

    def test_market_buy_success(self) -> None:
        m = MockAdapter(
            initial_price=Decimal("50000"),
            initial_quote_balance=Decimal("10000"),
            fee_rate=Decimal("0.001"),
            slippage_rate=Decimal("0.001"),
        )
        result = m.market_buy(Decimal("1000"))
        assert result.status == "filled"
        assert result.filled_qty > 0
        assert result.avg_fill_price > Decimal("50000")  # slippage
        assert result.fee > 0

        # Check balances updated
        b = m.get_balances()
        assert b["USDT"].free < Decimal("10000")
        assert b["BTC"].free > 0

    def test_market_buy_insufficient_balance(self) -> None:
        m = MockAdapter(initial_quote_balance=Decimal("100"))
        result = m.market_buy(Decimal("1000"))
        assert result.status == "failed"

    def test_market_sell_success(self) -> None:
        m = MockAdapter(
            initial_price=Decimal("50000"),
            initial_base_balance=Decimal("1.0"),
            fee_rate=Decimal("0.001"),
            slippage_rate=Decimal("0.001"),
        )
        result = m.market_sell(Decimal("0.5"))
        assert result.status == "filled"
        assert result.filled_qty == Decimal("0.5")
        assert result.avg_fill_price < Decimal("50000")  # slippage

        b = m.get_balances()
        assert b["BTC"].free == Decimal("0.5")
        assert b["USDT"].free > 0

    def test_market_sell_insufficient_balance(self) -> None:
        m = MockAdapter(initial_base_balance=Decimal("0"))
        result = m.market_sell(Decimal("1"))
        assert result.status == "failed"

    def test_buy_then_sell(self) -> None:
        m = MockAdapter(
            initial_price=Decimal("50000"),
            initial_quote_balance=Decimal("10000"),
        )
        buy = m.market_buy(Decimal("5000"))
        assert buy.status == "filled"

        # Now sell everything
        btc = m.get_balances()["BTC"].free
        sell = m.market_sell(btc)
        assert sell.status == "filled"

        # Should have slightly less than 10000 due to fees + slippage
        final_quote = m.get_balances()["USDT"].free
        assert final_quote < Decimal("10000")
        assert final_quote > Decimal("9900")  # not too much lost

    def test_custom_assets(self) -> None:
        m = MockAdapter(base_asset="ETH", quote_asset="USDC")
        assert m.base_asset == "ETH"
        assert m.quote_asset == "USDC"
