"""State models for executor state persistence."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass
class ExecutorState:
    """
    Persistent state for the strategy executor.

    Backwards-compatible with FearHarvester executor_state.json format.
    """

    version: int = 3
    exchange: str = "paper"
    strategy: str = "fear-greed-dca"
    mode: str = "paper"
    positions: list[dict[str, Any]] = field(default_factory=list)
    total_invested: float = 0.0
    last_action: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "version": self.version,
            "exchange": self.exchange,
            "strategy": self.strategy,
            "mode": self.mode,
            "positions": self.positions,
            "total_invested": self.total_invested,
            "last_action": self.last_action,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutorState":
        """Deserialize from dict."""
        return cls(
            version=data.get("version", 2),
            exchange=data.get("exchange", "paper"),
            strategy=data.get("strategy", "fear-greed-dca"),
            mode=data.get("mode", "paper"),
            positions=data.get("positions", []),
            total_invested=float(data.get("total_invested", 0.0)),
            last_action=data.get("last_action"),
        )

    @property
    def open_positions(self) -> list[dict[str, Any]]:
        """Return only open positions."""
        return [p for p in self.positions if p.get("status") == "open"]

    @property
    def total_invested_decimal(self) -> Decimal:
        """Total invested as Decimal."""
        return Decimal(str(self.total_invested))
