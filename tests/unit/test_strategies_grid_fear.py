"""Tests for GridFear strategy."""
from __future__ import annotations

from decimal import Decimal

import pytest

from fear_protocol.core.models import ActionType, MarketContext
from fear_protocol.strategies.grid_fear import GridFearConfig, GridFearStrategy


class TestGridFearStrategy:
    def test_name(self) -> None:
        s = GridFearStrategy()
        assert s.name == "grid-fear"

    def test_buy_in_fear_zone(self) -> None:
        s = GridFearStrategy()
        ctx = MarketContext(
            timestamp="t", fear_greed=15, fear_greed_label="EF",
            price=Decimal("20000"), portfolio_value=Decimal("10000"),
            total_invested=Decimal("0"), open_positions=[],
        )
        sig = s.evaluate(ctx)
        assert sig.action == ActionType.BUY
        assert sig.suggested_amount > 0

    def test_hold_outside_fear(self) -> None:
        s = GridFearStrategy()
        ctx = MarketContext(
            timestamp="t", fear_greed=45, fear_greed_label="Neutral",
            price=Decimal("25000"), portfolio_value=Decimal("10000"),
            total_invested=Decimal("0"), open_positions=[],
        )
        sig = s.evaluate(ctx)
        assert sig.action == ActionType.HOLD

    def test_grid_level_increases_amount(self) -> None:
        config = GridFearConfig(
            fear_threshold=30,
            grid_levels=5,
            grid_spacing_pct=5.0,
            base_amount_usd=Decimal("100"),
            level_multiplier=2.0,
        )
        s = GridFearStrategy(config=config)
        # First evaluation sets reference
        ctx0 = MarketContext(
            timestamp="t0", fear_greed=20, fear_greed_label="EF",
            price=Decimal("20000"), portfolio_value=Decimal("10000"),
            total_invested=Decimal("0"), open_positions=[],
        )
        sig0 = s.evaluate(ctx0)
        assert sig0.action == ActionType.BUY

        # Price drops 10% → level 2
        ctx1 = MarketContext(
            timestamp="t1", fear_greed=15, fear_greed_label="EF",
            price=Decimal("18000"), portfolio_value=Decimal("10000"),
            total_invested=Decimal("100"), open_positions=[],
        )
        sig1 = s.evaluate(ctx1)
        assert sig1.action == ActionType.BUY
        assert sig1.suggested_amount > sig0.suggested_amount

    def test_from_dict(self) -> None:
        s = GridFearStrategy.from_dict({"fear_threshold": 30, "grid_levels": 3})
        assert s.config.fear_threshold == 30
        assert s.config.grid_levels == 3
