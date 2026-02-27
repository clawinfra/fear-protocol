"""Smoke tests for FearProtocolAgent (agent/api.py)."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from fear_protocol.agent.api import FearProtocolAgent
from fear_protocol.agent.schemas import SignalSchema
from fear_protocol.data.fear_greed import FearGreedProvider
from fear_protocol.data.price import BinancePriceProvider


@pytest.fixture
def agent(monkeypatch: pytest.MonkeyPatch) -> FearProtocolAgent:
    monkeypatch.setattr(
        FearGreedProvider,
        "get_current",
        lambda _self: {"value": 25, "label": "Fear"},
    )
    monkeypatch.setattr(
        BinancePriceProvider,
        "get_price",
        lambda _self, symbol="BTCUSDT": Decimal("50000"),
    )
    return FearProtocolAgent(strategy="fear-greed-dca", exchange="mock", mode="dry-run")


class TestGetSignal:
    def test_returns_dict(self, agent: FearProtocolAgent) -> None:
        result = agent.get_signal()
        assert isinstance(result, dict)

    def test_has_required_keys(self, agent: FearProtocolAgent) -> None:
        result = agent.get_signal()
        assert "action" in result
        assert "confidence" in result
        assert "fear_greed" in result
        assert "price" in result

    def test_schema_valid(self, agent: FearProtocolAgent) -> None:
        result = agent.get_signal()
        schema = SignalSchema(**result)
        assert schema.action in ("BUY", "SELL", "HOLD")
        assert 0.0 <= schema.confidence <= 1.0

    def test_fear_greed_value(self, agent: FearProtocolAgent) -> None:
        result = agent.get_signal()
        assert result["fear_greed"] == 25
        assert result["fear_greed_label"] == "Fear"

    def test_strategy_field(self, agent: FearProtocolAgent) -> None:
        result = agent.get_signal()
        assert result["strategy"] == "fear-greed-dca"


class TestFromConfig:
    def test_from_config_creates_agent(self) -> None:
        config = {
            "strategy": "fear-greed-dca",
            "exchange": "paper",
            "mode": "dry-run",
        }
        agent = FearProtocolAgent.from_config(config)
        assert agent.strategy_name == "fear-greed-dca"
        assert agent.mode == "dry-run"

    def test_from_config_invalid_mode(self) -> None:
        with pytest.raises(Exception):
            FearProtocolAgent.from_config({"mode": "invalid-mode"})
