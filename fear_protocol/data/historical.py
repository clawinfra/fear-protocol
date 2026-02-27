"""Cached historical data provider for backtesting."""
from __future__ import annotations

import json
import time
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import requests


CACHE_DIR = Path.home() / ".fear-protocol" / "cache"
CACHE_TTL = 86400  # 24 hours


class HistoricalDataProvider:
    """
    Fetches and caches historical Fear & Greed and price data.

    Cache location: ~/.fear-protocol/cache/
    Cache TTL: 24 hours
    """

    def __init__(
        self,
        cache_dir: Path = CACHE_DIR,
        cache_ttl: int = CACHE_TTL,
        timeout: int = 30,
    ) -> None:
        """
        Initialize the historical data provider.

        Args:
            cache_dir: Directory to store cached data.
            cache_ttl: Cache TTL in seconds.
            timeout: HTTP request timeout in seconds.
        """
        self.cache_dir = cache_dir
        self.cache_ttl = cache_ttl
        self.timeout = timeout
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def _is_cache_valid(self, path: Path) -> bool:
        if not path.exists():
            return False
        age = time.time() - path.stat().st_mtime
        return age < self.cache_ttl

    def _load_cache(self, key: str) -> dict | list | None:
        path = self._cache_path(key)
        if self._is_cache_valid(path):
            return json.loads(path.read_text())
        return None

    def _save_cache(self, key: str, data: dict | list) -> None:
        path = self._cache_path(key)
        path.write_text(json.dumps(data))

    def get_fear_greed_history(
        self, start: str, end: str
    ) -> dict[str, int]:
        """
        Get historical Fear & Greed index values.

        Args:
            start: Start date 'YYYY-MM-DD'.
            end: End date 'YYYY-MM-DD'.

        Returns:
            Dict mapping 'YYYY-MM-DD' → F&G value (int).
        """
        cached = self._load_cache("fear_greed_history")
        if cached is None:
            resp = requests.get(
                "https://api.alternative.me/fng/",
                params={"limit": 2000, "format": "json"},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            raw = resp.json()["data"]
            all_data: dict[str, int] = {}
            for d in raw:
                date = datetime.fromtimestamp(int(d["timestamp"])).strftime("%Y-%m-%d")
                all_data[date] = int(d["value"])
            self._save_cache("fear_greed_history", all_data)
            cached = all_data

        # Filter by date range
        result: dict[str, int] = {}
        for date, value in cached.items():
            if start <= date <= end:
                result[date] = value
        return result

    def get_price_history(
        self, symbol: str, start: str, end: str
    ) -> dict[str, Decimal]:
        """
        Get historical daily close prices.

        Args:
            symbol: Trading pair (e.g. 'BTCUSDT').
            start: Start date 'YYYY-MM-DD'.
            end: End date 'YYYY-MM-DD'.

        Returns:
            Dict mapping 'YYYY-MM-DD' → close price.
        """
        cache_key = f"prices_{symbol}"
        cached = self._load_cache(cache_key)
        if cached is None:
            from datetime import timedelta

            # Fetch multiple chunks to cover long date ranges
            all_prices: dict[str, str] = {}
            start_dt = datetime.strptime("2017-01-01", "%Y-%m-%d")
            end_dt = datetime.now()
            chunk_start = start_dt

            while chunk_start < end_dt:
                chunk_end = min(
                    chunk_start + timedelta(days=1000), end_dt
                )
                start_ms = int(chunk_start.timestamp() * 1000)
                end_ms = int(chunk_end.timestamp() * 1000)

                resp = requests.get(
                    "https://api.binance.com/api/v3/klines",
                    params={
                        "symbol": symbol,
                        "interval": "1d",
                        "startTime": start_ms,
                        "endTime": end_ms,
                        "limit": 1000,
                    },
                    timeout=self.timeout,
                )
                resp.raise_for_status()
                klines = resp.json()
                for k in klines:
                    date = datetime.fromtimestamp(k[0] / 1000).strftime("%Y-%m-%d")
                    all_prices[date] = str(k[4])

                if not klines:
                    break
                chunk_start = chunk_end

            self._save_cache(cache_key, all_prices)
            cached = all_prices

        # Filter and convert to Decimal
        result: dict[str, Decimal] = {}
        for date, price in cached.items():
            if start <= date <= end:
                result[date] = Decimal(str(price))
        return result
