"""Tests for strategies __init__ get_strategy."""
from __future__ import annotations

import pytest

from fear_protocol.strategies import (
    get_strategy,
    STRATEGIES,
    FearGreedDCAStrategy,
    MomentumDCAStrategy,
    GridFearStrategy,
)


class TestGetStrategy:
    def test_fear_greed_dca(self):
        s = get_strategy("fear-greed-dca")
        assert isinstance(s, FearGreedDCAStrategy)

    def test_momentum_dca(self):
        s = get_strategy("momentum-dca")
        assert isinstance(s, MomentumDCAStrategy)

    def test_grid_fear(self):
        s = get_strategy("grid-fear")
        assert isinstance(s, GridFearStrategy)

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown strategy"):
            get_strategy("nonexistent")

    def test_with_params(self):
        params = {"dca_amount": "200", "extreme_fear_threshold": 15}
        s = get_strategy("fear-greed-dca", params=params)
        assert isinstance(s, FearGreedDCAStrategy)

    def test_strategies_registry_complete(self):
        assert "fear-greed-dca" in STRATEGIES
        assert "momentum-dca" in STRATEGIES
        assert "grid-fear" in STRATEGIES
