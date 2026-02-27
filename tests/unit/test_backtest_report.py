"""Tests for BacktestReport."""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from fear_protocol.backtest.report import BacktestReport
from fear_protocol.backtest.engine import BacktestEngine
from fear_protocol.core.models import BacktestConfig
from fear_protocol.strategies.fear_greed_dca import FearGreedDCAStrategy


def _make_result():
    config = BacktestConfig(
        strategy_name="fear-greed-dca",
        start_date="2024-01-01",
        end_date="2024-01-10",
        initial_capital=Decimal("10000"),
        fee_rate=Decimal("0.001"),
        slippage_rate=Decimal("0.0005"),
    )
    strategy = FearGreedDCAStrategy()
    engine = BacktestEngine(config, strategy)

    from datetime import date, timedelta

    fg: dict[str, int] = {}
    px: dict[str, Decimal] = {}
    d = date(2024, 1, 1)
    for i in range(10):
        key = d.strftime("%Y-%m-%d")
        fg[key] = 20  # extreme fear → buys
        px[key] = Decimal("40000") + Decimal(str(i * 500))
        d += timedelta(days=1)

    return engine.run(fg_data=fg, price_data=px)


class TestBacktestReport:
    def setup_method(self):
        self.result = _make_result()
        self.report = BacktestReport(self.result)

    def test_to_dict(self):
        d = self.report.to_dict()
        assert "strategy" in d
        assert "total_return_pct" in d

    def test_to_json(self, tmp_path: Path):
        out = tmp_path / "report.json"
        self.report.to_json(out)
        assert out.exists()
        data = json.loads(out.read_text())
        assert "strategy" in data

    def test_to_json_creates_parent_dirs(self, tmp_path: Path):
        out = tmp_path / "subdir" / "nested" / "report.json"
        self.report.to_json(out)
        assert out.exists()

    def test_to_markdown_contains_header(self):
        md = self.report.to_markdown()
        assert "# Backtest Results" in md
        assert "Sharpe" in md

    def test_to_markdown_deploy_verdict(self):
        md = self.report.to_markdown()
        assert "DEPLOY" in md or "NEEDS WORK" in md

    def test_print_summary_no_error(self, capsys):
        # Should not raise even without Rich
        self.report.print_summary()
