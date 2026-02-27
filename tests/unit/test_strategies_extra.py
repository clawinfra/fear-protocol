"""Additional tests to boost coverage on strategies and backtest."""
from __future__ import annotations

from decimal import Decimal
from datetime import datetime, timedelta

import pytest

from fear_protocol.core.models import ActionType, MarketContext
from fear_protocol.strategies.momentum_dca import MomentumDCAConfig, MomentumDCAStrategy
from fear_protocol.strategies.grid_fear import GridFearConfig, GridFearStrategy
from fear_protocol.strategies.fear_greed_dca import FearGreedDCAConfig, FearGreedDCAStrategy


class TestMomentumDCASellPath:
    def test_sell_on_recovery(self) -> None:
        """Test sell when F&G ≥ sell_threshold and positions eligible."""
        config = MomentumDCAConfig(sell_threshold=50, hold_days=1)
        s = MomentumDCAStrategy(config=config)
        old_ts = (datetime.now() - timedelta(days=10)).isoformat()
        ctx = MarketContext(
            timestamp="t", fear_greed=60, fear_greed_label="Greed",
            price=Decimal("30000"), portfolio_value=Decimal("10000"),
            total_invested=Decimal("1000"),
            open_positions=[{
                "timestamp": old_ts,
                "entry_price": 20000.0,
                "btc_qty": 0.05,
                "usd_amount": 1000.0,
                "fg_at_entry": 15,
                "status": "open",
                "mode": "test",
            }],
        )
        sig = s.evaluate(ctx)
        assert sig.action == ActionType.SELL

    def test_hold_positions_not_eligible(self) -> None:
        """Sell threshold met but positions not old enough."""
        config = MomentumDCAConfig(sell_threshold=50, hold_days=365)
        s = MomentumDCAStrategy(config=config)
        ctx = MarketContext(
            timestamp="t", fear_greed=60, fear_greed_label="Greed",
            price=Decimal("30000"), portfolio_value=Decimal("10000"),
            total_invested=Decimal("1000"),
            open_positions=[{
                "timestamp": datetime.now().isoformat(),
                "entry_price": 20000.0,
                "btc_qty": 0.05,
                "usd_amount": 1000.0,
                "fg_at_entry": 15,
                "status": "open",
                "mode": "test",
            }],
        )
        sig = s.evaluate(ctx)
        assert sig.action == ActionType.HOLD

    def test_max_capital_prevents_buy(self) -> None:
        config = MomentumDCAConfig(max_capital_usd=Decimal("100"))
        s = MomentumDCAStrategy(config=config)
        prices = [Decimal("25000"), Decimal("24000"), Decimal("23000"), Decimal("22000")]
        for i, price in enumerate(prices):
            ctx = MarketContext(
                timestamp=f"t{i}", fear_greed=15, fear_greed_label="EF",
                price=price, portfolio_value=Decimal("10000"),
                total_invested=Decimal("100"), open_positions=[],
            )
            sig = s.evaluate(ctx)
        assert sig.action == ActionType.HOLD

    def test_closed_positions_ignored(self) -> None:
        """Closed positions should not trigger sell."""
        config = MomentumDCAConfig(sell_threshold=50, hold_days=1)
        s = MomentumDCAStrategy(config=config)
        old_ts = (datetime.now() - timedelta(days=10)).isoformat()
        ctx = MarketContext(
            timestamp="t", fear_greed=60, fear_greed_label="Greed",
            price=Decimal("30000"), portfolio_value=Decimal("10000"),
            total_invested=Decimal("0"),
            open_positions=[{
                "timestamp": old_ts,
                "status": "closed",
                "btc_qty": 0.05,
            }],
        )
        sig = s.evaluate(ctx)
        assert sig.action == ActionType.HOLD

    def test_bad_timestamp_ignored(self) -> None:
        """Positions with bad timestamps should be silently skipped."""
        config = MomentumDCAConfig(sell_threshold=50, hold_days=1)
        s = MomentumDCAStrategy(config=config)
        ctx = MarketContext(
            timestamp="t", fear_greed=60, fear_greed_label="Greed",
            price=Decimal("30000"), portfolio_value=Decimal("10000"),
            total_invested=Decimal("0"),
            open_positions=[{
                "timestamp": "bad-date",
                "status": "open",
                "btc_qty": 0.05,
            }],
        )
        sig = s.evaluate(ctx)
        assert sig.action == ActionType.HOLD


class TestGridFearSellPath:
    def test_sell_on_recovery(self) -> None:
        config = GridFearConfig(sell_threshold=50, hold_days=1)
        s = GridFearStrategy(config=config)
        old_ts = (datetime.now() - timedelta(days=10)).isoformat()
        ctx = MarketContext(
            timestamp="t", fear_greed=60, fear_greed_label="Greed",
            price=Decimal("30000"), portfolio_value=Decimal("10000"),
            total_invested=Decimal("1000"),
            open_positions=[{
                "timestamp": old_ts,
                "entry_price": 20000.0,
                "btc_qty": 0.05,
                "usd_amount": 1000.0,
                "fg_at_entry": 15,
                "status": "open",
                "mode": "test",
            }],
        )
        sig = s.evaluate(ctx)
        assert sig.action == ActionType.SELL

    def test_max_capital_limits_buy(self) -> None:
        config = GridFearConfig(max_capital_usd=Decimal("100"), base_amount_usd=Decimal("200"))
        s = GridFearStrategy(config=config)
        ctx = MarketContext(
            timestamp="t", fear_greed=15, fear_greed_label="EF",
            price=Decimal("20000"), portfolio_value=Decimal("10000"),
            total_invested=Decimal("95"), open_positions=[],
        )
        sig = s.evaluate(ctx)
        # Only $5 remaining, below $10 min → should hold
        assert sig.action == ActionType.HOLD

    def test_reference_price_reset_on_sell(self) -> None:
        config = GridFearConfig(sell_threshold=50, hold_days=1)
        s = GridFearStrategy(config=config)
        # First set reference via fear zone
        ctx1 = MarketContext(
            timestamp="t1", fear_greed=15, fear_greed_label="EF",
            price=Decimal("20000"), portfolio_value=Decimal("10000"),
            total_invested=Decimal("0"), open_positions=[],
        )
        s.evaluate(ctx1)
        assert s._reference_price is not None

        # Now trigger sell
        old_ts = (datetime.now() - timedelta(days=10)).isoformat()
        ctx2 = MarketContext(
            timestamp="t2", fear_greed=60, fear_greed_label="Greed",
            price=Decimal("30000"), portfolio_value=Decimal("10000"),
            total_invested=Decimal("1000"),
            open_positions=[{
                "timestamp": old_ts,
                "btc_qty": 0.05,
                "status": "open",
            }],
        )
        sig = s.evaluate(ctx2)
        assert sig.action == ActionType.SELL
        assert s._reference_price is None

    def test_closed_positions_ignored(self) -> None:
        config = GridFearConfig(sell_threshold=50, hold_days=1)
        s = GridFearStrategy(config=config)
        old_ts = (datetime.now() - timedelta(days=10)).isoformat()
        ctx = MarketContext(
            timestamp="t", fear_greed=60, fear_greed_label="Greed",
            price=Decimal("30000"), portfolio_value=Decimal("10000"),
            total_invested=Decimal("0"),
            open_positions=[{"timestamp": old_ts, "status": "closed", "btc_qty": 0.05}],
        )
        sig = s.evaluate(ctx)
        assert sig.action == ActionType.HOLD

    def test_bad_timestamp_ignored(self) -> None:
        config = GridFearConfig(sell_threshold=50, hold_days=1)
        s = GridFearStrategy(config=config)
        ctx = MarketContext(
            timestamp="t", fear_greed=60, fear_greed_label="Greed",
            price=Decimal("30000"), portfolio_value=Decimal("10000"),
            total_invested=Decimal("0"),
            open_positions=[{"timestamp": "bad", "status": "open", "btc_qty": 0.05}],
        )
        sig = s.evaluate(ctx)
        assert sig.action == ActionType.HOLD


class TestFearGreedDCAEdgeCases:
    def test_fg_zero_confidence(self) -> None:
        s = FearGreedDCAStrategy()
        assert s._fear_confidence(0) == 1.0

    def test_fg_at_threshold(self) -> None:
        s = FearGreedDCAStrategy()
        c = s._fear_confidence(20)
        assert c == pytest.approx(0.5)

    def test_eligible_positions_bad_timestamp(self) -> None:
        s = FearGreedDCAStrategy(FearGreedDCAConfig(sell_threshold=50, hold_days=1))
        ctx = MarketContext(
            timestamp="t", fear_greed=60, fear_greed_label="Greed",
            price=Decimal("30000"), portfolio_value=Decimal("10000"),
            total_invested=Decimal("0"),
            open_positions=[{"timestamp": "not-a-date", "status": "open"}],
        )
        sig = s.evaluate(ctx)
        assert sig.action == ActionType.HOLD

    def test_eligible_positions_missing_timestamp(self) -> None:
        s = FearGreedDCAStrategy(FearGreedDCAConfig(sell_threshold=50, hold_days=1))
        ctx = MarketContext(
            timestamp="t", fear_greed=60, fear_greed_label="Greed",
            price=Decimal("30000"), portfolio_value=Decimal("10000"),
            total_invested=Decimal("0"),
            open_positions=[{"status": "open"}],
        )
        sig = s.evaluate(ctx)
        assert sig.action == ActionType.HOLD

    def test_zero_buy_threshold_confidence(self) -> None:
        config = FearGreedDCAConfig(buy_threshold=0, sell_threshold=50)
        s = FearGreedDCAStrategy(config=config)
        assert s._fear_confidence(0) == 1.0

    def test_validate_config_valid(self) -> None:
        s = FearGreedDCAStrategy()
        s.validate_config()  # should not raise


class TestBacktestReportPrintSummary:
    def test_print_summary_with_rich(self) -> None:
        """Ensure print_summary doesn't crash."""
        from fear_protocol.backtest.report import BacktestReport
        from fear_protocol.core.models import BacktestConfig, BacktestResult

        result = BacktestResult(
            config=BacktestConfig(
                strategy_name="test",
                start_date="2023-01-01",
                end_date="2023-12-31",
                initial_capital=Decimal("10000"),
            ),
            ticks=[],
            trades=[],
            total_return_pct=25.0,
            annualized_return_pct=25.0,
            sharpe_ratio=1.8,
            sortino_ratio=2.5,
            max_drawdown_pct=-15.0,
            calmar_ratio=1.67,
            win_rate_pct=70.0,
            avg_win_pct=15.0,
            avg_loss_pct=-5.0,
            profit_factor=3.0,
            total_trades=10,
            avg_hold_days=90.0,
            btc_hold_return_pct=50.0,
            alpha=-25.0,
        )
        report = BacktestReport(result)
        report.print_summary()  # Just verify it doesn't crash
