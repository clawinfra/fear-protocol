"""Tests for data providers (mock/unit level, no network calls)."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from fear_protocol.data.price import MockPriceProvider, BinancePriceProvider
from fear_protocol.data.fear_greed import FearGreedProvider
from fear_protocol.data.base import AbstractDataProvider


class TestMockPriceProvider:
    def test_get_price_returns_default(self):
        provider = MockPriceProvider({}, default=Decimal("50000"))
        assert provider.get_price() == Decimal("50000")

    def test_get_daily_closes_returns_all(self):
        prices = {"2024-01-01": Decimal("40000"), "2024-01-02": Decimal("41000")}
        provider = MockPriceProvider(prices)
        result = provider.get_daily_closes()
        assert result == prices

    def test_get_price_custom_default(self):
        provider = MockPriceProvider({}, default=Decimal("99999"))
        assert provider.get_price("ETHUSDT") == Decimal("99999")

    def test_get_daily_closes_with_symbol(self):
        prices = {"2024-01-01": Decimal("3000")}
        provider = MockPriceProvider(prices)
        result = provider.get_daily_closes("ETHUSDT")
        assert result == prices


class TestBinancePriceProviderMocked:
    def test_get_price(self):
        provider = BinancePriceProvider(timeout=5)
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"price": "45000.50"}
        mock_resp.raise_for_status = MagicMock()

        with patch("fear_protocol.data.price.requests.get", return_value=mock_resp):
            price = provider.get_price("BTCUSDT")

        assert price == Decimal("45000.50")

    def test_get_daily_closes(self):
        provider = BinancePriceProvider(timeout=5)
        # Kline: [open_time, open, high, low, close, ...]
        mock_klines = [
            [1704067200000, "39900", "40500", "39800", "40250.00", "100"],
            [1704153600000, "40250", "41000", "40100", "40800.00", "120"],
        ]
        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_klines
        mock_resp.raise_for_status = MagicMock()

        with patch("fear_protocol.data.price.requests.get", return_value=mock_resp):
            closes = provider.get_daily_closes("BTCUSDT")

        assert len(closes) == 2
        for v in closes.values():
            assert isinstance(v, Decimal)

    def test_get_daily_closes_with_start_end_time(self):
        provider = BinancePriceProvider(timeout=5)
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()

        with patch("fear_protocol.data.price.requests.get", return_value=mock_resp) as mock_get:
            provider.get_daily_closes(start_time=1000, end_time=2000)

        call_kwargs = mock_get.call_args
        assert call_kwargs is not None


class TestFearGreedProviderMocked:
    def test_get_current(self):
        provider = FearGreedProvider(timeout=5)
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": [{"value": "35", "value_classification": "Fear", "timestamp": "1704067200"}]
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("fear_protocol.data.fear_greed.requests.get", return_value=mock_resp):
            result = provider.get_current()

        assert result["value"] == 35
        assert result["label"] == "Fear"
        assert "timestamp" in result

    def test_get_history(self):
        provider = FearGreedProvider(timeout=5)
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": [
                {"value": "20", "value_classification": "Extreme Fear", "timestamp": "1704067200"},
                {"value": "50", "value_classification": "Neutral", "timestamp": "1703980800"},
            ]
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("fear_protocol.data.fear_greed.requests.get", return_value=mock_resp):
            history = provider.get_history(limit=2)

        assert len(history) == 2
        assert history[0]["value"] == 20
        assert "date" in history[0]
        assert "label" in history[0]


class TestAbstractDataProvider:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            AbstractDataProvider()  # type: ignore[abstract]

    def test_concrete_implementation_works(self):
        class ConcreteProvider(AbstractDataProvider):
            def get_current_fear_greed(self):
                return {"value": 50, "label": "Neutral", "timestamp": "2024-01-01"}

            def get_current_price(self, symbol="BTCUSDT"):
                return Decimal("40000")

        p = ConcreteProvider()
        assert p.get_current_fear_greed()["value"] == 50
        assert p.get_current_price() == Decimal("40000")
