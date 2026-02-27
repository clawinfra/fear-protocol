"""Price data providers (Binance, CoinGecko)."""
from __future__ import annotations

from decimal import Decimal

import requests


class BinancePriceProvider:
    """Fetch current and historical prices from Binance."""

    BASE_URL = "https://api.binance.com/api/v3"

    def __init__(self, timeout: int = 10) -> None:
        """
        Initialize provider.

        Args:
            timeout: HTTP request timeout in seconds.
        """
        self.timeout = timeout

    def get_price(self, symbol: str = "BTCUSDT") -> Decimal:
        """
        Get current price for a symbol.

        Args:
            symbol: Trading pair symbol (e.g. 'BTCUSDT').

        Returns:
            Current price as Decimal.

        Raises:
            requests.RequestException: On network error.
        """
        resp = requests.get(
            f"{self.BASE_URL}/ticker/price",
            params={"symbol": symbol},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return Decimal(resp.json()["price"])

    def get_daily_closes(
        self,
        symbol: str = "BTCUSDT",
        limit: int = 1000,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> dict[str, Decimal]:
        """
        Get daily close prices indexed by date string.

        Args:
            symbol: Trading pair symbol.
            limit: Number of candles (max 1000 per request).
            start_time: Start timestamp in milliseconds.
            end_time: End timestamp in milliseconds.

        Returns:
            Dict mapping 'YYYY-MM-DD' → close price.
        """
        from datetime import datetime

        params: dict[str, int | str] = {
            "symbol": symbol,
            "interval": "1d",
            "limit": limit,
        }
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time

        resp = requests.get(
            f"{self.BASE_URL}/klines",
            params=params,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        klines = resp.json()
        result: dict[str, Decimal] = {}
        for k in klines:
            date = datetime.fromtimestamp(k[0] / 1000).strftime("%Y-%m-%d")
            result[date] = Decimal(str(k[4]))  # close price
        return result


class MockPriceProvider:
    """Deterministic mock price provider for testing."""

    def __init__(self, prices: dict[str, Decimal], default: Decimal = Decimal("50000")) -> None:
        """
        Initialize mock provider.

        Args:
            prices: Dict mapping 'YYYY-MM-DD' → price.
            default: Default price if date not in prices.
        """
        self.prices = prices
        self.default = default

    def get_price(self, symbol: str = "BTCUSDT") -> Decimal:
        """Return default price (use for current price lookups)."""
        return self.default

    def get_daily_closes(self, symbol: str = "BTCUSDT", **kwargs: object) -> dict[str, Decimal]:
        """Return all mock prices."""
        return dict(self.prices)
