"""Tests for the FearGreedDCA strategy."""
from __future__ import annotations

from decimal import Decimal

import pytest

from fear_protocol.core.models import ActionType, MarketContext
from fear_protocol.strategies.fear_greed_dca import FearGreedDCAConfig, FearGreedDCAStrategy


class TestFearGreedDCAStrategy:
    def test_name_and_description(self) -> None:
        s = FearGreedDCAStrategy()
        assert s.name == "fear-greed-dca"
        assert "fear" in s.description.lower()

    def test_buy_on_extreme_fear(self, base_market_ctx: MarketContext) -> None:
        s = FearGreedDCAStrategy()
        sig = s.evaluate(base_market_ctx)
        assert sig.action == ActionType.BUY
        assert sig.confidence >= 0.5
        assert sig.suggested_amount == Decimal("500")

    def test_hold_in_neutral(self, neutral_market_ctx: MarketContext) -> None:
        s = FearGreedDCAStrategy()
        sig = s.evaluate(neutral_market_ctx)
        assert sig.action == ActionType.HOLD

    def test_sell_on_greed_with_eligible(self, greed_market_ctx: MarketContext) -> None:
        config = FearGreedDCAConfig(hold_days=1)  # 1 day so positions are eligible
        s = FearGreedDCAStrategy(config=config)
        sig = s.evaluate(greed_market_ctx)
        assert sig.action == ActionType.SELL

    def test_hold_when_max_capital_reached(self) -> None:
        ctx = MarketContext(
            timestamp="2023-01-01T12:00:00",
            fear_greed=10,
            fear_greed_label="Extreme Fear",
            price=Decimal("20000"),
            portfolio_value=Decimal("5000"),
            total_invested=Decimal("5000"),  # At max
            open_positions=[],
        )
        s = FearGreedDCAStrategy()
        sig = s.evaluate(ctx)
        assert sig.action == ActionType.HOLD
        assert "max capital" in sig.reason

    def test_fear_confidence_increases_with_depth(self) -> None:
        s = FearGreedDCAStrategy()
        # Deeper fear = higher confidence
        ctx_10 = MarketContext(
            timestamp="t", fear_greed=10, fear_greed_label="EF",
            price=Decimal("20000"), portfolio_value=Decimal("10000"),
            total_invested=Decimal("0"), open_positions=[],
        )
        ctx_20 = MarketContext(
            timestamp="t", fear_greed=20, fear_greed_label="EF",
            price=Decimal("20000"), portfolio_value=Decimal("10000"),
            total_invested=Decimal("0"), open_positions=[],
        )
        sig_10 = s.evaluate(ctx_10)
        sig_20 = s.evaluate(ctx_20)
        assert sig_10.confidence >= sig_20.confidence

    def test_custom_thresholds(self) -> None:
        config = FearGreedDCAConfig(buy_threshold=30, sell_threshold=70)
        s = FearGreedDCAStrategy(config=config)
        ctx = MarketContext(
            timestamp="t", fear_greed=25, fear_greed_label="Fear",
            price=Decimal("20000"), portfolio_value=Decimal("10000"),
            total_invested=Decimal("0"), open_positions=[],
        )
        sig = s.evaluate(ctx)
        assert sig.action == ActionType.BUY

    def test_from_dict(self) -> None:
        s = FearGreedDCAStrategy.from_dict({
            "buy_threshold": 15,
            "sell_threshold": 60,
            "hold_days": 90,
            "dca_amount_usd": 1000,
        })
        assert s.config.buy_threshold == 15
        assert s.config.sell_threshold == 60
        assert s.config.hold_days == 90
        assert s.config.dca_amount_usd == Decimal("1000")


class TestFearGreedDCAConfig:
    def test_validate_buy_threshold_range(self) -> None:
        config = FearGreedDCAConfig(buy_threshold=150)
        with pytest.raises(ValueError, match="buy_threshold"):
            config.validate()

    def test_validate_buy_gte_sell(self) -> None:
        config = FearGreedDCAConfig(buy_threshold=60, sell_threshold=50)
        with pytest.raises(ValueError, match="buy_threshold.*sell_threshold"):
            config.validate()

    def test_validate_negative_hold(self) -> None:
        config = FearGreedDCAConfig(hold_days=0)
        with pytest.raises(ValueError, match="hold_days"):
            config.validate()

    def test_validate_negative_amount(self) -> None:
        config = FearGreedDCAConfig(dca_amount_usd=Decimal("-100"))
        with pytest.raises(ValueError, match="dca_amount_usd"):
            config.validate()

    def test_valid_config(self) -> None:
        config = FearGreedDCAConfig()
        config.validate()  # Should not raise
