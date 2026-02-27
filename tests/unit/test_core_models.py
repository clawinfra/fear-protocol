"""Tests for core domain models."""
from __future__ import annotations

from decimal import Decimal

import pytest

from fear_protocol.core.models import (
    ActionType,
    Balance,
    BacktestConfig,
    MarketContext,
    MarketPrice,
    OrderResult,
    Position,
    StrategySignal,
)


class TestBalance:
    def test_total_property(self) -> None:
        b = Balance(asset="BTC", free=Decimal("1.5"), locked=Decimal("0.5"))
        assert b.total == Decimal("2.0")

    def test_total_zero_locked(self) -> None:
        b = Balance(asset="USDT", free=Decimal("1000"), locked=Decimal("0"))
        assert b.total == Decimal("1000")


class TestMarketPrice:
    def test_mid_property(self) -> None:
        p = MarketPrice(
            symbol="BTC/USDT",
            bid=Decimal("49900"),
            ask=Decimal("50100"),
            last=Decimal("50000"),
        )
        assert p.mid == Decimal("50000")

    def test_mid_asymmetric(self) -> None:
        p = MarketPrice(
            symbol="BTC/USDT",
            bid=Decimal("100"),
            ask=Decimal("200"),
            last=Decimal("150"),
        )
        assert p.mid == Decimal("150")


class TestPosition:
    def test_unrealized_pnl_open(self) -> None:
        pos = Position(
            timestamp="2023-01-01",
            entry_price=Decimal("20000"),
            base_qty=Decimal("0.1"),
            quote_amount=Decimal("2000"),
            fg_at_entry=15,
            status="open",
            mode="test",
        )
        pnl = pos.unrealized_pnl(Decimal("25000"))
        assert pnl == Decimal("500")  # 0.1 * 25000 - 2000

    def test_unrealized_pnl_closed_is_zero(self) -> None:
        pos = Position(
            timestamp="2023-01-01",
            entry_price=Decimal("20000"),
            base_qty=Decimal("0.1"),
            quote_amount=Decimal("2000"),
            fg_at_entry=15,
            status="closed",
            mode="test",
        )
        assert pos.unrealized_pnl(Decimal("25000")) == Decimal("0")

    def test_to_dict_and_from_dict(self) -> None:
        pos = Position(
            timestamp="2023-01-01T12:00:00",
            entry_price=Decimal("20000"),
            base_qty=Decimal("0.1"),
            quote_amount=Decimal("2000"),
            fg_at_entry=15,
            status="open",
            mode="paper",
        )
        d = pos.to_dict()
        assert d["entry_price"] == 20000.0
        assert d["btc_qty"] == 0.1
        assert d["status"] == "open"

        pos2 = Position.from_dict(d)
        assert pos2.entry_price == pos.entry_price
        assert pos2.base_qty == pos.base_qty
        assert pos2.status == pos.status


class TestStrategySignal:
    def test_default_metadata(self) -> None:
        sig = StrategySignal(
            action=ActionType.HOLD,
            confidence=1.0,
            reason="test",
            suggested_amount=Decimal("0"),
        )
        assert sig.metadata == {}

    def test_action_enum_values(self) -> None:
        assert ActionType.BUY.value == "BUY"
        assert ActionType.SELL.value == "SELL"
        assert ActionType.HOLD.value == "HOLD"


class TestOrderResult:
    def test_default_raw(self) -> None:
        r = OrderResult(
            order_id="123",
            status="filled",
            filled_qty=Decimal("0.1"),
            avg_fill_price=Decimal("20000"),
            fee=Decimal("2"),
        )
        assert r.raw == {}


class TestBacktestConfig:
    def test_default_values(self) -> None:
        cfg = BacktestConfig(
            strategy_name="fear-greed-dca",
            start_date="2020-01-01",
            end_date="2024-01-01",
            initial_capital=Decimal("10000"),
        )
        assert cfg.fee_rate == Decimal("0.001")
        assert cfg.slippage_rate == Decimal("0.001")
        assert cfg.data_source == "binance"
