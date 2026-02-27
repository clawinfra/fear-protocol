"""Tests for core.math financial utilities."""
from __future__ import annotations

import math
from decimal import Decimal

import pytest

from fear_protocol.core.math import (
    annualized_return,
    calmar_ratio,
    kelly_fraction,
    max_drawdown,
    position_size_usd,
    profit_factor,
    sharpe_ratio,
    sortino_ratio,
)


class TestSharpeRatio:
    def test_positive_returns(self) -> None:
        returns = [10.0, 5.0, 15.0, 8.0, 12.0]
        sr = sharpe_ratio(returns)
        assert sr > 0

    def test_mixed_returns(self) -> None:
        returns = [10.0, -5.0, 15.0, -3.0, 8.0]
        sr = sharpe_ratio(returns)
        assert sr > 0  # net positive

    def test_single_return(self) -> None:
        assert sharpe_ratio([5.0]) == 0.0

    def test_empty_returns(self) -> None:
        assert sharpe_ratio([]) == 0.0

    def test_zero_std(self) -> None:
        assert sharpe_ratio([5.0, 5.0, 5.0]) == 0.0

    def test_with_risk_free_rate(self) -> None:
        returns = [10.0, 15.0, 12.0, 8.0]
        sr = sharpe_ratio(returns, risk_free_rate=2.0)
        assert sr > 0


class TestSortinoRatio:
    def test_all_positive(self) -> None:
        returns = [5.0, 10.0, 15.0]
        sr = sortino_ratio(returns)
        assert sr == float("inf")

    def test_mixed_returns(self) -> None:
        returns = [10.0, -5.0, 15.0, -3.0]
        sr = sortino_ratio(returns)
        assert sr > 0

    def test_single_return(self) -> None:
        assert sortino_ratio([5.0]) == 0.0

    def test_empty(self) -> None:
        assert sortino_ratio([]) == 0.0


class TestMaxDrawdown:
    def test_no_drawdown(self) -> None:
        curve = [100.0, 110.0, 120.0, 130.0]
        assert max_drawdown(curve) == 0.0

    def test_simple_drawdown(self) -> None:
        curve = [100.0, 120.0, 90.0, 110.0]
        dd = max_drawdown(curve)
        assert dd == pytest.approx(-25.0)  # 90/120 - 1 = -25%

    def test_deep_drawdown(self) -> None:
        curve = [100.0, 200.0, 100.0]
        dd = max_drawdown(curve)
        assert dd == pytest.approx(-50.0)

    def test_single_point(self) -> None:
        assert max_drawdown([100.0]) == 0.0

    def test_empty(self) -> None:
        assert max_drawdown([]) == 0.0


class TestCalmarRatio:
    def test_positive(self) -> None:
        assert calmar_ratio(20.0, -10.0) == pytest.approx(2.0)

    def test_zero_drawdown(self) -> None:
        assert calmar_ratio(20.0, 0.0) == 0.0


class TestAnnualizedReturn:
    def test_one_year_100pct(self) -> None:
        ar = annualized_return(100.0, 365)
        assert ar == pytest.approx(100.0, rel=0.01)

    def test_two_years(self) -> None:
        ar = annualized_return(100.0, 730)
        # (2.0)^(1/2) - 1 ≈ 41.4%
        assert ar == pytest.approx(41.4, rel=0.05)

    def test_zero_days(self) -> None:
        assert annualized_return(50.0, 0) == 0.0

    def test_negative_return(self) -> None:
        ar = annualized_return(-50.0, 365)
        assert ar < 0


class TestKellyFraction:
    def test_positive_edge(self) -> None:
        k = kelly_fraction(0.6, 0.2, 0.1)
        assert 0.0 < k <= 1.0

    def test_no_edge(self) -> None:
        k = kelly_fraction(0.5, 0.1, 0.1)
        assert k == 0.0

    def test_zero_loss(self) -> None:
        assert kelly_fraction(0.5, 0.1, 0.0) == 0.0

    def test_clamped_to_one(self) -> None:
        k = kelly_fraction(0.99, 10.0, 0.01)
        assert k <= 1.0


class TestProfitFactor:
    def test_basic(self) -> None:
        wins = [100.0, 50.0]
        losses = [-30.0, -20.0]
        pf = profit_factor(wins, losses)
        assert pf == pytest.approx(3.0)

    def test_no_losses(self) -> None:
        pf = profit_factor([100.0], [])
        assert pf == float("inf")  # no losses = infinite profit factor

    def test_no_wins(self) -> None:
        pf = profit_factor([], [-50.0])
        assert pf == pytest.approx(0.0)


class TestPositionSizeUsd:
    def test_basic(self) -> None:
        size = position_size_usd(
            Decimal("10000"), 0.25, Decimal("500")
        )
        assert size == Decimal("500")  # capped at max

    def test_kelly_limited(self) -> None:
        size = position_size_usd(
            Decimal("10000"), 0.01, Decimal("500")
        )
        assert size == Decimal("100")  # 1% of 10000
