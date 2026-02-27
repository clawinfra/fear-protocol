"""Tests for agent Pydantic schemas."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from fear_protocol.agent.schemas import (
    BacktestRequestSchema,
    ExecuteResultSchema,
    RunConfigSchema,
    SignalSchema,
)


class TestSignalSchema:
    def test_valid_signal(self) -> None:
        s = SignalSchema(
            timestamp="2023-01-01T12:00:00",
            action="BUY",
            confidence=0.85,
            fear_greed=15,
            fear_greed_label="Extreme Fear",
            price=20000.0,
            reason="F&G=15 ≤ 20",
            suggested_amount=500.0,
            strategy="fear-greed-dca",
        )
        d = s.model_dump()
        assert d["action"] == "BUY"
        assert d["confidence"] == 0.85

    def test_invalid_confidence(self) -> None:
        with pytest.raises(ValidationError):
            SignalSchema(
                timestamp="t", action="BUY", confidence=1.5,
                fear_greed=15, fear_greed_label="EF", price=20000.0,
                reason="r", suggested_amount=500.0, strategy="s",
            )

    def test_invalid_fg(self) -> None:
        with pytest.raises(ValidationError):
            SignalSchema(
                timestamp="t", action="BUY", confidence=0.5,
                fear_greed=150, fear_greed_label="EF", price=20000.0,
                reason="r", suggested_amount=500.0, strategy="s",
            )


class TestExecuteResultSchema:
    def test_dry_run_result(self) -> None:
        r = ExecuteResultSchema(
            timestamp="2023-01-01T12:00:00",
            action="HOLD",
            success=True,
            dry_run=True,
            mode="dry-run",
        )
        assert r.dry_run is True
        assert r.fill is None


class TestBacktestRequestSchema:
    def test_valid_request(self) -> None:
        r = BacktestRequestSchema(
            strategy="fear-greed-dca",
            start_date="2020-01-01",
            initial_capital=10000.0,
        )
        assert r.strategy == "fear-greed-dca"

    def test_invalid_strategy(self) -> None:
        with pytest.raises(ValidationError, match="Unknown strategy"):
            BacktestRequestSchema(strategy="nonexistent")


class TestRunConfigSchema:
    def test_defaults(self) -> None:
        r = RunConfigSchema()
        assert r.strategy == "fear-greed-dca"
        assert r.exchange == "paper"
        assert r.mode == "dry-run"

    def test_invalid_mode(self) -> None:
        with pytest.raises(ValidationError):
            RunConfigSchema(mode="yolo")  # type: ignore[arg-type]
