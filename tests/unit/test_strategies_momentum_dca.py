"""Tests for the MomentumDCA strategy."""
from __future__ import annotations

from decimal import Decimal

import pytest

from fear_protocol.core.models import ActionType, MarketContext
from fear_protocol.strategies.momentum_dca import MomentumDCAConfig, MomentumDCAStrategy


class TestMomentumDCAStrategy:
    def test_name(self) -> None:
        s = MomentumDCAStrategy()
        assert s.name == "momentum-dca"

    def test_hold_without_consecutive_down(self) -> None:
        s = MomentumDCAStrategy()
        ctx = MarketContext(
            timestamp="t", fear_greed=15, fear_greed_label="EF",
            price=Decimal("20000"), portfolio_value=Decimal("10000"),
            total_invested=Decimal("0"), open_positions=[],
        )
        sig = s.evaluate(ctx)
        # Only 1 price point, no consecutive down pattern
        assert sig.action == ActionType.HOLD

    def test_buy_after_consecutive_down(self) -> None:
        s = MomentumDCAStrategy(MomentumDCAConfig(min_consecutive_down=3))
        prices = [Decimal("25000"), Decimal("24000"), Decimal("23000"), Decimal("22000")]
        for i, price in enumerate(prices):
            ctx = MarketContext(
                timestamp=f"t{i}", fear_greed=15, fear_greed_label="EF",
                price=price, portfolio_value=Decimal("10000"),
                total_invested=Decimal("0"), open_positions=[],
            )
            sig = s.evaluate(ctx)
        # After 3 consecutive downs in fear zone → BUY
        assert sig.action == ActionType.BUY

    def test_hold_in_neutral_zone(self) -> None:
        s = MomentumDCAStrategy()
        ctx = MarketContext(
            timestamp="t", fear_greed=45, fear_greed_label="Neutral",
            price=Decimal("20000"), portfolio_value=Decimal("10000"),
            total_invested=Decimal("0"), open_positions=[],
        )
        sig = s.evaluate(ctx)
        assert sig.action == ActionType.HOLD

    def test_from_dict(self) -> None:
        s = MomentumDCAStrategy.from_dict({"fear_threshold": 25, "min_consecutive_down": 5})
        assert s.config.fear_threshold == 25
        assert s.config.min_consecutive_down == 5
