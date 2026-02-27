"""Tests for the PaperAdapter exchange (mocked network calls)."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest

from fear_protocol.exchanges.paper import PaperAdapter


class TestPaperAdapter:
    def test_name(self) -> None:
        a = PaperAdapter()
        assert a.name == "paper"
        assert a.base_asset == "BTC"
        assert a.quote_asset == "USDT"

    def test_initial_balances(self) -> None:
        a = PaperAdapter(initial_quote=Decimal("5000"))
        b = a.get_balances()
        assert b["USDT"].free == Decimal("5000")
        assert b["BTC"].free == Decimal("0")

    @patch("fear_protocol.exchanges.paper.requests.get")
    def test_get_price(self, mock_get: MagicMock) -> None:
        mock_get.return_value.json.return_value = {
            "bidPrice": "50000.00",
            "askPrice": "50010.00",
        }
        mock_get.return_value.raise_for_status = MagicMock()
        a = PaperAdapter()
        p = a.get_price()
        assert p.bid == Decimal("50000.00")
        assert p.ask == Decimal("50010.00")

    @patch("fear_protocol.exchanges.paper.requests.get")
    def test_market_buy(self, mock_get: MagicMock) -> None:
        mock_get.return_value.json.return_value = {
            "bidPrice": "50000.00",
            "askPrice": "50010.00",
        }
        mock_get.return_value.raise_for_status = MagicMock()
        a = PaperAdapter(initial_quote=Decimal("10000"))
        result = a.market_buy(Decimal("1000"))
        assert result.status == "filled"
        assert result.filled_qty > 0
        b = a.get_balances()
        assert b["USDT"].free < Decimal("10000")
        assert b["BTC"].free > 0

    @patch("fear_protocol.exchanges.paper.requests.get")
    def test_market_buy_insufficient(self, mock_get: MagicMock) -> None:
        a = PaperAdapter(initial_quote=Decimal("100"))
        result = a.market_buy(Decimal("1000"))
        assert result.status == "failed"

    @patch("fear_protocol.exchanges.paper.requests.get")
    def test_market_sell(self, mock_get: MagicMock) -> None:
        mock_get.return_value.json.return_value = {
            "bidPrice": "50000.00",
            "askPrice": "50010.00",
        }
        mock_get.return_value.raise_for_status = MagicMock()
        # First buy some BTC
        a = PaperAdapter(initial_quote=Decimal("10000"))
        a.market_buy(Decimal("5000"))
        btc = a.get_balances()["BTC"].free
        assert btc > 0

        # Now sell
        result = a.market_sell(btc)
        assert result.status == "filled"

    def test_market_sell_insufficient(self) -> None:
        a = PaperAdapter()
        result = a.market_sell(Decimal("1"))
        assert result.status == "failed"

    @patch("fear_protocol.exchanges.paper.requests.get")
    def test_state_persistence(self, mock_get: MagicMock, tmp_path) -> None:
        mock_get.return_value.json.return_value = {
            "bidPrice": "50000.00",
            "askPrice": "50010.00",
        }
        mock_get.return_value.raise_for_status = MagicMock()
        state_file = tmp_path / "paper_state.json"
        a = PaperAdapter(initial_quote=Decimal("10000"), state_file=state_file)
        a.market_buy(Decimal("1000"))
        assert state_file.exists()

        # Load again
        a2 = PaperAdapter(state_file=state_file)
        b = a2.get_balances()
        assert b["USDT"].free < Decimal("10000")
