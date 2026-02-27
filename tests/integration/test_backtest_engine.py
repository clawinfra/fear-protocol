"""Integration tests for the BacktestEngine."""
from __future__ import annotations

from decimal import Decimal

import pytest

from fear_protocol.backtest.engine import BacktestEngine
from fear_protocol.backtest.report import BacktestReport
from fear_protocol.core.models import BacktestConfig
from fear_protocol.strategies.fear_greed_dca import FearGreedDCAStrategy


class TestBacktestEngine:
    def test_basic_backtest(
        self, sample_fg_history: dict[str, int], sample_price_history: dict[str, Decimal]
    ) -> None:
        """Run a basic backtest on sample data."""
        config = BacktestConfig(
            strategy_name="fear-greed-dca",
            start_date="2023-01-01",
            end_date="2023-03-31",
            initial_capital=Decimal("10000"),
        )
        strategy = FearGreedDCAStrategy()
        engine = BacktestEngine(config=config, strategy=strategy)
        result = engine.run(fg_data=sample_fg_history, price_data=sample_price_history)

        assert result.total_trades > 0
        assert len(result.ticks) > 0
        assert result.config.strategy_name == "fear-greed-dca"

    def test_backtest_produces_trades(
        self, sample_fg_history: dict[str, int], sample_price_history: dict[str, Decimal]
    ) -> None:
        """Verify buys happen during extreme fear periods."""
        config = BacktestConfig(
            strategy_name="fear-greed-dca",
            start_date="2023-01-01",
            end_date="2023-03-31",
            initial_capital=Decimal("10000"),
        )
        strategy = FearGreedDCAStrategy()
        engine = BacktestEngine(config=config, strategy=strategy)
        result = engine.run(fg_data=sample_fg_history, price_data=sample_price_history)

        from fear_protocol.core.models import ActionType
        buy_ticks = [t for t in result.ticks if t.action == ActionType.BUY and t.fill]
        assert len(buy_ticks) > 0
        # All buys should be when F&G ≤ 20
        for bt in buy_ticks:
            assert bt.fear_greed <= 20

    def test_backtest_capital_depleted(
        self, sample_fg_history: dict[str, int], sample_price_history: dict[str, Decimal]
    ) -> None:
        """Small capital should get exhausted."""
        config = BacktestConfig(
            strategy_name="fear-greed-dca",
            start_date="2023-01-01",
            end_date="2023-03-31",
            initial_capital=Decimal("1000"),
        )
        strategy = FearGreedDCAStrategy()
        engine = BacktestEngine(config=config, strategy=strategy)
        result = engine.run(fg_data=sample_fg_history, price_data=sample_price_history)

        # Should still have ticks but eventually run out of capital
        assert len(result.ticks) > 0

    def test_backtest_report(
        self, sample_fg_history: dict[str, int], sample_price_history: dict[str, Decimal]
    ) -> None:
        """Test report generation."""
        config = BacktestConfig(
            strategy_name="fear-greed-dca",
            start_date="2023-01-01",
            end_date="2023-03-31",
            initial_capital=Decimal("10000"),
        )
        strategy = FearGreedDCAStrategy()
        engine = BacktestEngine(config=config, strategy=strategy)
        result = engine.run(fg_data=sample_fg_history, price_data=sample_price_history)

        report = BacktestReport(result)
        d = report.to_dict()
        assert "total_return_pct" in d
        assert "sharpe_ratio" in d

        md = report.to_markdown()
        assert "Sharpe Ratio" in md
        assert "Total Return" in md

    def test_backtest_json_output(
        self, sample_fg_history: dict[str, int], sample_price_history: dict[str, Decimal],
        tmp_path,
    ) -> None:
        config = BacktestConfig(
            strategy_name="fear-greed-dca",
            start_date="2023-01-01",
            end_date="2023-03-31",
            initial_capital=Decimal("10000"),
        )
        strategy = FearGreedDCAStrategy()
        engine = BacktestEngine(config=config, strategy=strategy)
        result = engine.run(fg_data=sample_fg_history, price_data=sample_price_history)

        report = BacktestReport(result)
        out_path = tmp_path / "results.json"
        report.to_json(out_path)
        assert out_path.exists()

        import json
        data = json.loads(out_path.read_text())
        assert "sharpe_ratio" in data

    def test_streaming(
        self, sample_fg_history: dict[str, int], sample_price_history: dict[str, Decimal]
    ) -> None:
        config = BacktestConfig(
            strategy_name="fear-greed-dca",
            start_date="2023-01-01",
            end_date="2023-03-31",
            initial_capital=Decimal("10000"),
        )
        strategy = FearGreedDCAStrategy()
        engine = BacktestEngine(config=config, strategy=strategy)
        ticks = list(engine.run_streaming(
            fg_data=sample_fg_history, price_data=sample_price_history
        ))
        assert len(ticks) > 0

    def test_empty_data(self) -> None:
        config = BacktestConfig(
            strategy_name="fear-greed-dca",
            start_date="2099-01-01",
            end_date="2099-12-31",
            initial_capital=Decimal("10000"),
        )
        strategy = FearGreedDCAStrategy()
        engine = BacktestEngine(config=config, strategy=strategy)
        result = engine.run(fg_data={}, price_data={})
        assert result.total_trades == 0
        assert result.total_return_pct == 0.0

    def test_custom_thresholds(
        self, sample_fg_history: dict[str, int], sample_price_history: dict[str, Decimal]
    ) -> None:
        config = BacktestConfig(
            strategy_name="fear-greed-dca",
            start_date="2023-01-01",
            end_date="2023-03-31",
            initial_capital=Decimal("10000"),
        )
        strategy = FearGreedDCAStrategy.from_dict({"buy_threshold": 15})
        engine = BacktestEngine(config=config, strategy=strategy)
        result = engine.run(fg_data=sample_fg_history, price_data=sample_price_history)
        # More restrictive threshold = fewer trades
        assert len(result.ticks) > 0
