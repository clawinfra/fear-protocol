"""Pydantic schemas for agent I/O."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class SignalSchema(BaseModel):
    """Output schema for a signal check."""

    timestamp: str
    action: Literal["BUY", "SELL", "HOLD"]
    confidence: float = Field(ge=0.0, le=1.0)
    fear_greed: int = Field(ge=0, le=100)
    fear_greed_label: str
    price: float
    reason: str
    suggested_amount: float
    strategy: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class OrderFillSchema(BaseModel):
    """Schema for an executed order fill."""

    order_id: str
    status: str
    filled_qty: float
    avg_fill_price: float
    fee: float


class ExecuteResultSchema(BaseModel):
    """Output schema for a strategy execution result."""

    timestamp: str
    action: str
    success: bool
    fill: Optional[OrderFillSchema] = None
    error: Optional[str] = None
    dry_run: bool = False
    mode: str = "paper"


class BacktestRequestSchema(BaseModel):
    """Input schema for a backtest request."""

    strategy: str = "fear-greed-dca"
    start_date: str = "2020-01-01"
    end_date: str = "2024-12-31"
    initial_capital: float = 10000.0
    fee_rate: float = 0.001
    slippage_rate: float = 0.001
    strategy_params: dict[str, Any] = Field(default_factory=dict)

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        """Validate strategy name is known."""
        from fear_protocol.strategies import STRATEGIES

        if v not in STRATEGIES:
            raise ValueError(f"Unknown strategy: {v!r}. Available: {list(STRATEGIES)}")
        return v


class RunConfigSchema(BaseModel):
    """Input schema for a run configuration."""

    strategy: str = "fear-greed-dca"
    exchange: str = "paper"
    mode: Literal["dry-run", "paper", "live"] = "dry-run"
    strategy_params: dict[str, Any] = Field(default_factory=dict)
    testnet: bool = False
