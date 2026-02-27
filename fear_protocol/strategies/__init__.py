"""Strategy registry and exports for fear-protocol."""
from __future__ import annotations

from typing import Any

from fear_protocol.strategies.base import AbstractStrategy
from fear_protocol.strategies.fear_greed_dca import FearGreedDCAStrategy
from fear_protocol.strategies.grid_fear import GridFearStrategy
from fear_protocol.strategies.momentum_dca import MomentumDCAStrategy

STRATEGIES: dict[str, type[AbstractStrategy]] = {
    "fear-greed-dca": FearGreedDCAStrategy,
    "momentum-dca": MomentumDCAStrategy,
    "grid-fear": GridFearStrategy,
}

__all__ = [
    "AbstractStrategy",
    "FearGreedDCAStrategy",
    "MomentumDCAStrategy",
    "GridFearStrategy",
    "STRATEGIES",
    "get_strategy",
]


def get_strategy(name: str, params: dict[str, Any] | None = None) -> AbstractStrategy:
    """
    Get a strategy by name.

    Args:
        name: Strategy name ('fear-greed-dca', 'momentum-dca', 'grid-fear').
        params: Optional strategy parameters.

    Returns:
        Configured strategy instance.

    Raises:
        ValueError: If strategy name is unknown.
    """
    if name not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {name!r}. Available: {list(STRATEGIES)}")
    cls = STRATEGIES[name]
    if params and hasattr(cls, "from_dict"):
        return cls.from_dict(params)  # type: ignore[union-attr]
    return cls()
