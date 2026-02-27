"""Fear & Greed index provider from alternative.me."""
from __future__ import annotations

from datetime import datetime
from typing import Any

import requests


ALTERNATIVE_ME_URL = "https://api.alternative.me/fng/"


class FearGreedProvider:
    """
    Fetches Fear & Greed index from alternative.me API.

    API docs: https://alternative.me/crypto/fear-and-greed-index/
    """

    def __init__(self, timeout: int = 10) -> None:
        """
        Initialize provider.

        Args:
            timeout: HTTP request timeout in seconds.
        """
        self.timeout = timeout

    def get_current(self) -> dict[str, Any]:
        """
        Get current Fear & Greed index.

        Returns:
            Dict with 'value' (int), 'label' (str), 'timestamp' (str).

        Raises:
            requests.RequestException: On network error.
        """
        resp = requests.get(
            ALTERNATIVE_ME_URL,
            params={"limit": 1},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()["data"][0]
        return {
            "value": int(data["value"]),
            "label": data["value_classification"],
            "timestamp": datetime.fromtimestamp(int(data["timestamp"])).isoformat(),
        }

    def get_history(self, limit: int = 2000) -> list[dict[str, Any]]:
        """
        Get Fear & Greed history.

        Args:
            limit: Number of days to fetch (max 2000).

        Returns:
            List of dicts with 'date' (YYYY-MM-DD), 'value' (int), 'label' (str).

        Raises:
            requests.RequestException: On network error.
        """
        resp = requests.get(
            ALTERNATIVE_ME_URL,
            params={"limit": limit, "format": "json"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        raw = resp.json()["data"]
        result = []
        for d in raw:
            date = datetime.fromtimestamp(int(d["timestamp"])).strftime("%Y-%m-%d")
            result.append({
                "date": date,
                "value": int(d["value"]),
                "label": d["value_classification"],
            })
        return result
