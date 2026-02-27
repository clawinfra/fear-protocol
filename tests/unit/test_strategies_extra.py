"""Extra tests for grid_fear and momentum_dca to improve coverage."""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from fear_protocol.core.models import ActionType, MarketContext


def _ctx(
    fg: int = 25,
    price: Decimal = Decimal("40000"),
    total_invested: Decimal = Decimal("0"),
    open_positions: list | None = None,
) -> MarketContext:
    return MarketContext(
        timestamp="2024-01-01",
        fear_greed=fg,
        fear_greed_label="Fear",
        price=price,
        portfolio_value=Decimal("10000"),
        total_invested=total_invested,
        open_positions=open_positions or [],
    )


class TestGridFearStrategyExtra:
    def test_hold_when_neutral(self):
        from fear_protocol.strategies.grid_fear import GridFearStrategy

        s = GridFearStrategy()
        ctx = _ctx(fg=50)
        sig = s.evaluate(ctx)
        assert sig.action == ActionType.HOLD

    def test_buy_in_fear_zone(self):
        from fear_protocol.strategies.grid_fear import GridFearStrategy

        s = GridFearStrategy()
        ctx = _ctx(fg=20, price=Decimal("40000"))
        sig = s.evaluate(ctx)
        assert sig.action == ActionType.BUY
        assert sig.suggested_amount > 0

    def test_sell_in_greed_zone_with_old_position(self):
        from fear_protocol.strategies.grid_fear import GridFearStrategy, GridFearConfig

        config = GridFearConfig(sell_threshold=70, hold_days=0)
        s = GridFearStrategy(config=config)
        old_ts = (datetime.now() - timedelta(days=10)).isoformat()
        positions = [{"status": "open", "timestamp": old_ts, "btc_qty": 0.01}]
        ctx = _ctx(fg=75, open_positions=positions)
        sig = s.evaluate(ctx)
        assert sig.action == ActionType.SELL

    def test_no_sell_when_positions_too_new(self):
        from fear_protocol.strategies.grid_fear import GridFearStrategy, GridFearConfig

        config = GridFearConfig(sell_threshold=70, hold_days=30)
        s = GridFearStrategy(config=config)
        new_ts = datetime.now().isoformat()
        positions = [{"status": "open", "timestamp": new_ts, "btc_qty": 0.01}]
        ctx = _ctx(fg=75, open_positions=positions)
        sig = s.evaluate(ctx)
        # Not enough hold days, should HOLD
        assert sig.action == ActionType.HOLD

    def test_grid_level_increases_with_drop(self):
        from fear_protocol.strategies.grid_fear import GridFearStrategy

        s = GridFearStrategy()
        # Set reference price via first eval
        ctx1 = _ctx(fg=20, price=Decimal("40000"))
        s.evaluate(ctx1)
        # Now price dropped significantly
        ctx2 = _ctx(fg=20, price=Decimal("36000"))  # 10% drop → level 1
        sig = s.evaluate(ctx2)
        assert sig.action == ActionType.BUY
        assert sig.metadata.get("grid_level", 0) >= 1

    def test_from_dict(self):
        from fear_protocol.strategies.grid_fear import GridFearStrategy

        s = GridFearStrategy.from_dict({"fear_threshold": 30, "base_amount_usd": "300"})
        assert s.config.fear_threshold == 30

    def test_cap_at_max_capital(self):
        from fear_protocol.strategies.grid_fear import GridFearStrategy, GridFearConfig

        config = GridFearConfig(max_capital_usd=Decimal("200"), base_amount_usd=Decimal("500"))
        s = GridFearStrategy(config=config)
        ctx = _ctx(fg=15, total_invested=Decimal("150"))
        sig = s.evaluate(ctx)
        if sig.action == ActionType.BUY:
            assert sig.suggested_amount <= Decimal("50")

    def test_max_capital_exceeded_holds(self):
        from fear_protocol.strategies.grid_fear import GridFearStrategy, GridFearConfig

        config = GridFearConfig(max_capital_usd=Decimal("100"))
        s = GridFearStrategy(config=config)
        ctx = _ctx(fg=15, total_invested=Decimal("200"))  # already over cap
        sig = s.evaluate(ctx)
        assert sig.action == ActionType.HOLD

    def test_eligible_positions_invalid_timestamp(self):
        from fear_protocol.strategies.grid_fear import GridFearStrategy, GridFearConfig

        config = GridFearConfig(sell_threshold=70, hold_days=0)
        s = GridFearStrategy(config=config)
        positions = [{"status": "open", "timestamp": "not-a-date", "btc_qty": 0.01}]
        ctx = _ctx(fg=75, open_positions=positions)
        sig = s.evaluate(ctx)
        # Invalid timestamp → skipped, no positions → HOLD
        assert sig.action == ActionType.HOLD

    def test_reference_price_reset_on_sell(self):
        from fear_protocol.strategies.grid_fear import GridFearStrategy, GridFearConfig

        config = GridFearConfig(sell_threshold=70, hold_days=0)
        s = GridFearStrategy(config=config)
        # Set reference
        ctx1 = _ctx(fg=20, price=Decimal("40000"))
        s.evaluate(ctx1)
        assert s._reference_price is not None

        # Trigger sell
        old_ts = (datetime.now() - timedelta(days=10)).isoformat()
        positions = [{"status": "open", "timestamp": old_ts, "btc_qty": 0.01}]
        ctx2 = _ctx(fg=75, open_positions=positions)
        s.evaluate(ctx2)
        assert s._reference_price is None


class TestMomentumDCAStrategyExtra:
    def test_hold_without_enough_down_days(self):
        from fear_protocol.strategies.momentum_dca import MomentumDCAStrategy, MomentumDCAConfig

        config = MomentumDCAConfig(min_consecutive_down=3, fear_threshold=30)
        s = MomentumDCAStrategy(config=config)
        prices = [Decimal("40000"), Decimal("39500"), Decimal("39000")]
        for p in prices:
            ctx = _ctx(fg=25, price=p)
            sig = s.evaluate(ctx)
        # Only 2 consecutive down — need 3
        assert sig.action == ActionType.HOLD

    def test_buy_after_consecutive_down_days(self):
        from fear_protocol.strategies.momentum_dca import MomentumDCAStrategy, MomentumDCAConfig

        config = MomentumDCAConfig(min_consecutive_down=3, fear_threshold=30)
        s = MomentumDCAStrategy(config=config)
        prices = [Decimal("40000"), Decimal("39500"), Decimal("39000"), Decimal("38500")]
        for p in prices:
            ctx = _ctx(fg=25, price=p)
            sig = s.evaluate(ctx)
        assert sig.action == ActionType.BUY

    def test_sell_in_greed_with_eligible_position(self):
        from fear_protocol.strategies.momentum_dca import MomentumDCAStrategy, MomentumDCAConfig

        config = MomentumDCAConfig(sell_threshold=70, hold_days=0)
        s = MomentumDCAStrategy(config=config)
        old_ts = (datetime.now() - timedelta(days=10)).isoformat()
        positions = [{"status": "open", "timestamp": old_ts, "btc_qty": 0.01}]
        ctx = _ctx(fg=75, open_positions=positions)
        sig = s.evaluate(ctx)
        assert sig.action == ActionType.SELL

    def test_count_consecutive_down_empty(self):
        from fear_protocol.strategies.momentum_dca import MomentumDCAStrategy

        s = MomentumDCAStrategy()
        assert s._count_consecutive_down() == 0

    def test_count_consecutive_down_up_day(self):
        from fear_protocol.strategies.momentum_dca import MomentumDCAStrategy

        s = MomentumDCAStrategy()
        s._price_history = [Decimal("39000"), Decimal("40000")]  # up day
        assert s._count_consecutive_down() == 0

    def test_price_history_trimmed(self):
        from fear_protocol.strategies.momentum_dca import MomentumDCAStrategy, MomentumDCAConfig

        config = MomentumDCAConfig(min_consecutive_down=2)
        s = MomentumDCAStrategy(config=config)
        for i in range(20):
            s.update_price_history(Decimal(str(40000 - i * 100)))
        # History should be trimmed to min_consecutive_down + 1 = 3
        assert len(s._price_history) <= config.min_consecutive_down + 1

    def test_from_dict(self):
        from fear_protocol.strategies.momentum_dca import MomentumDCAStrategy

        s = MomentumDCAStrategy.from_dict({"fear_threshold": 20, "min_consecutive_down": 2})
        assert s.config.fear_threshold == 20

    def test_no_sell_when_positions_too_new(self):
        from fear_protocol.strategies.momentum_dca import MomentumDCAStrategy, MomentumDCAConfig

        config = MomentumDCAConfig(sell_threshold=70, hold_days=30)
        s = MomentumDCAStrategy(config=config)
        new_ts = datetime.now().isoformat()
        positions = [{"status": "open", "timestamp": new_ts, "btc_qty": 0.01}]
        ctx = _ctx(fg=75, open_positions=positions)
        sig = s.evaluate(ctx)
        assert sig.action == ActionType.HOLD

    def test_eligible_positions_invalid_timestamp(self):
        from fear_protocol.strategies.momentum_dca import MomentumDCAStrategy, MomentumDCAConfig

        config = MomentumDCAConfig(sell_threshold=70, hold_days=0)
        s = MomentumDCAStrategy(config=config)
        positions = [{"status": "open", "timestamp": "bad-ts", "btc_qty": 0.01}]
        ctx = _ctx(fg=75, open_positions=positions)
        sig = s.evaluate(ctx)
        assert sig.action == ActionType.HOLD
