"""Exchange adapters for fear-protocol."""
from __future__ import annotations

from fear_protocol.exchanges.base import AbstractExchangeAdapter
from fear_protocol.exchanges.mock import MockAdapter
from fear_protocol.exchanges.paper import PaperAdapter

__all__ = ["AbstractExchangeAdapter", "MockAdapter", "PaperAdapter", "get_adapter"]


def get_adapter(name: str, **kwargs: object) -> AbstractExchangeAdapter:
    """
    Get an exchange adapter by name.

    Args:
        name: Adapter name ('mock', 'paper', 'hyperliquid', 'binance').
        **kwargs: Passed to adapter constructor.

    Returns:
        Configured exchange adapter.

    Raises:
        ValueError: If adapter name is unknown.
    """
    if name == "mock":
        return MockAdapter(**kwargs)  # type: ignore[arg-type]
    elif name == "paper":
        return PaperAdapter(**kwargs)  # type: ignore[arg-type]
    elif name == "hyperliquid":
        from fear_protocol.exchanges.hyperliquid import HyperliquidAdapter
        return HyperliquidAdapter(**kwargs)  # type: ignore[arg-type]
    else:
        raise ValueError(f"Unknown exchange: {name!r}. Available: mock, paper, hyperliquid")
