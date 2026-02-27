"""Shared test fixtures for fear-protocol."""
from __future__ import annotations

from decimal import Decimal
from datetime import datetime, timedelta

import pytest

from fear_protocol.core.models import MarketContext, Position


@pytest.fixture
def sample_fg_history() -> dict[str, int]:
    """Sample Fear & Greed history (90 days)."""
    data: dict[str, int] = {}
    start = datetime(2023, 1, 1)
    values = [
        15, 18, 12, 20, 25, 30, 35, 40, 45, 50,
        55, 60, 65, 70, 75, 70, 65, 60, 55, 50,
        45, 40, 35, 30, 25, 20, 18, 15, 10, 12,
        14, 18, 20, 22, 25, 30, 35, 40, 45, 50,
        52, 55, 58, 60, 62, 65, 70, 72, 75, 78,
        75, 72, 70, 68, 65, 62, 60, 58, 55, 52,
        50, 48, 45, 42, 40, 38, 35, 32, 30, 28,
        25, 22, 20, 18, 15, 12, 10, 8, 12, 15,
        18, 20, 22, 25, 28, 30, 32, 35, 38, 40,
    ]
    for i, v in enumerate(values):
        date = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        data[date] = v
    return data


@pytest.fixture
def sample_price_history() -> dict[str, Decimal]:
    """Sample BTC price history (90 days, trending up)."""
    data: dict[str, Decimal] = {}
    start = datetime(2023, 1, 1)
    base_price = Decimal("20000")
    for i in range(90):
        date = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        # Simple upward trend with noise
        price = base_price + Decimal(str(i * 100)) + Decimal(str((i % 7 - 3) * 200))
        data[date] = max(Decimal("15000"), price)
    return data


@pytest.fixture
def base_market_ctx() -> MarketContext:
    """A standard market context for testing (extreme fear = BUY)."""
    return MarketContext(
        timestamp="2023-01-01T12:00:00",
        fear_greed=15,
        fear_greed_label="Extreme Fear",
        price=Decimal("20000"),
        portfolio_value=Decimal("10000"),
        total_invested=Decimal("0"),
        open_positions=[],
    )


@pytest.fixture
def greed_market_ctx() -> MarketContext:
    """A market context in greed zone."""
    return MarketContext(
        timestamp="2023-07-01T12:00:00",
        fear_greed=70,
        fear_greed_label="Greed",
        price=Decimal("35000"),
        portfolio_value=Decimal("12000"),
        total_invested=Decimal("2000"),
        open_positions=[
            {
                "timestamp": "2023-01-01T12:00:00",
                "entry_price": 20000.0,
                "btc_qty": 0.1,
                "usd_amount": 2000.0,
                "fg_at_entry": 15,
                "status": "open",
                "mode": "test",
            }
        ],
    )


@pytest.fixture
def neutral_market_ctx() -> MarketContext:
    """A market context in neutral zone."""
    return MarketContext(
        timestamp="2023-04-01T12:00:00",
        fear_greed=45,
        fear_greed_label="Neutral",
        price=Decimal("28000"),
        portfolio_value=Decimal("10500"),
        total_invested=Decimal("1000"),
        open_positions=[],
    )
