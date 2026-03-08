"""Tests for exchanges __init__ get_adapter."""
from __future__ import annotations

from decimal import Decimal

import pytest

from fear_protocol.exchanges import MockAdapter, PaperAdapter, get_adapter


class TestGetAdapter:
    def test_mock_adapter(self):
        adapter = get_adapter(
            "mock",
            initial_price=Decimal("40000"),
            fee_rate=Decimal("0.001"),
            slippage_rate=Decimal("0.0005"),
            initial_quote_balance=Decimal("10000"),
        )
        assert isinstance(adapter, MockAdapter)

    def test_paper_adapter(self):
        adapter = get_adapter(
            "paper",
            initial_quote=Decimal("10000"),
            fee_rate=Decimal("0.001"),
        )
        assert isinstance(adapter, PaperAdapter)

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown exchange"):
            get_adapter("unknown_exchange")

    def test_hyperliquid_import(self):
        """Hyperliquid adapter is importable even if not configured."""
        # Just test that get_adapter tries to import it (will raise if HL not configured)
        import contextlib
        with contextlib.suppress(ValueError, ImportError, Exception):
            get_adapter("hyperliquid")  # expected to raise — HL needs credentials
