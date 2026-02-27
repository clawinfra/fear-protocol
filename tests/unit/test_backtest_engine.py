"""Tests for the BacktestEngine and helpers."""
from __future__ import annotations

from decimal import Decimal

import pytest

from fear_protocol.backtest.engine import BacktestEngine, _fg_label
from fear_protocol.core.models import BacktestConfig, ActionType
from fear_protocol.strategies.fear_greed_dca import FearGreedDCAStrategy


def _make_config(
    start: str = "2024-01-01",
    end: str = "2024-01-10",
    capital: Decimal = Decimal("10000"),
) -> BacktestConfig:
    return BacktestConfig(
        strategy_name="fear-greed-dca",
        start_date=start,
        end_date=end,
        initial_capital=capital,
        fee_rate=Decimal("0.001"),
        slippage_rate=Decimal("0.0005"),
    )


def _make_data() -> tuple[dict[str, int], dict[str, Decimal]]:
    fg = {
        f"2024-01-{d:02d}": v
        for d, v in [
            (1, 10), (2, 15), (3, 20), (4, 30), (5, 40),
            (6, 50), (7, 60), (8, 70), (9, 55), (10, 45),
        ]
    }
    prices = {
        f"2024-01-{d:02d}": Decimal(str(p))
        for d, p in [
            (1, 42000), (2, 41000), (3, 40000), (4, 42000), (5, 43000),
            (6, 44000), (7, 45000), (8, 46000), (9, 44000), (10, 43000),
        ]
    }
    return fg, prices


class TestFgLabel:
    def test_extreme_fear(self) -> None:
        assert _fg_label(10) == "Extreme Fear"

    def test_fear(self) -> None:
        assert _fg_label(30) == "Fear"

    def test_neutral(self) -> None:
        assert _fg_label(50) == "Neutral"

    def test_greed(self) -> None:
        assert _fg_label(70) == "Greed"

    def test_extreme_greed(self) -> None:
        assert _fg_label(90) == "Extreme Greed"


class TestBacktestEngineBasic:
    def test_run_returns_result(self) -> None:
        config = _make_config()
        strategy = FearGreedDCAStrategy()
        engine = BacktestEngine(config=config, strategy=strategy)
        fg, prices = _make_data()
        result = engine.run(fg_data=fg, price_data=prices)
        assert result.total_trades > 0
        assert len(result.ticks) == 10

    def test_run_empty_data(self) -> None:
        config = _make_config()
        strategy = FearGreedDCAStrategy()
        engine = BacktestEngine(config=config, strategy=strategy)
        result = engine.run(fg_data={}, price_data={})
        assert result.total_trades == 0

    def test_run_streaming_yields_ticks(self) -> None:
        config = _make_config()
        strategy = FearGreedDCAStrategy()
        engine = BacktestEngine(config=config, strategy=strategy)
        fg, prices = _make_data()
        ticks = list(engine.run_streaming(fg_data=fg, price_data=prices))
        assert len(ticks) == 10

    def test_run_no_overlap_data(self) -> None:
        config = _make_config()
        strategy = FearGreedDCAStrategy()
        engine = BacktestEngine(config=config, strategy=strategy)
        fg = {"2025-01-01": 10}
        prices = {"2024-01-01": Decimal("40000")}
        result = engine.run(fg_data=fg, price_data=prices)
        assert result.total_trades == 0

    def test_data_filtered_by_date_range(self) -> None:
        config = _make_config(start="2024-01-03", end="2024-01-07")
        strategy = FearGreedDCAStrategy()
        engine = BacktestEngine(config=config, strategy=strategy)
        fg, prices = _make_data()
        result = engine.run(fg_data=fg, price_data=prices)
        assert len(result.ticks) == 5

    def test_result_has_btc_benchmark(self) -> None:
        config = _make_config()
        strategy = FearGreedDCAStrategy()
        engine = BacktestEngine(config=config, strategy=strategy)
        fg, prices = _make_data()
        result = engine.run(fg_data=fg, price_data=prices)
        # BTC went from 42000 to 43000
        assert result.btc_hold_return_pct != 0.0

    def test_result_metrics_range(self) -> None:
        config = _make_config()
        strategy = FearGreedDCAStrategy()
        engine = BacktestEngine(config=config, strategy=strategy)
        fg, prices = _make_data()
        result = engine.run(fg_data=fg, price_data=prices)
        assert -100 <= result.total_return_pct <= 1000
        assert result.max_drawdown_pct <= 0
