"""Hyperliquid spot adapter for UBTC/USDC. Ported from FearHarvester."""
from __future__ import annotations

import os
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any

from fear_protocol.core.models import Balance, MarketPrice, OrderResult
from fear_protocol.exchanges.base import AbstractExchangeAdapter


# Hyperliquid UBTC/USDC pair constants
UBTC_PAIR = "@142"
UBTC_SZ_DECIMALS = 5
UBTC_PX_DECIMALS = 0

HL_ENV_PATH = Path.home() / ".openclaw/skills/hyperliquid/.env"


def load_hl_credentials() -> tuple[str | None, str | None]:
    """
    Load HL credentials from environment or .env file.

    Returns:
        Tuple of (private_key, wallet_address), either may be None.
    """
    if HL_ENV_PATH.exists():
        for line in HL_ENV_PATH.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    private_key = os.environ.get("HL_PRIVATE_KEY") or os.environ.get("PRIVATE_KEY")
    wallet_address = os.environ.get("HL_WALLET_ADDRESS") or os.environ.get("WALLET_ADDRESS")
    return private_key, wallet_address


class HyperliquidAdapter(AbstractExchangeAdapter):
    """
    Hyperliquid spot adapter for UBTC/USDC.

    Ported from FearHarvester HLSpotExecutor.
    Implements the AbstractExchangeAdapter interface.
    """

    @property
    def name(self) -> str:
        """Exchange name."""
        return "hyperliquid"

    @property
    def base_asset(self) -> str:
        """Base asset symbol."""
        return "UBTC"

    @property
    def quote_asset(self) -> str:
        """Quote asset symbol."""
        return "USDC"

    def __init__(
        self,
        private_key: str | None = None,
        wallet_address: str | None = None,
        testnet: bool = False,
    ) -> None:
        """
        Initialize the Hyperliquid adapter.

        Args:
            private_key: Ethereum private key for signing orders.
            wallet_address: Wallet address (derived from key if not provided).
            testnet: Use HL testnet instead of mainnet.
        """
        self.private_key = private_key
        self.wallet_address = wallet_address
        self.testnet = testnet
        self._exchange: Any = None
        self._info: Any = None

    @classmethod
    def from_env(cls, testnet: bool = False) -> "HyperliquidAdapter":
        """
        Create adapter by loading credentials from environment.

        Args:
            testnet: Use HL testnet.

        Returns:
            Configured HyperliquidAdapter.

        Raises:
            ValueError: If no credentials found.
        """
        private_key, wallet_address = load_hl_credentials()
        if not private_key:
            raise ValueError(
                "HL_PRIVATE_KEY required. Set via environment or "
                f"{HL_ENV_PATH}"
            )
        return cls(
            private_key=private_key,
            wallet_address=wallet_address,
            testnet=testnet,
        )

    @property
    def _hl_exchange(self) -> Any:
        """Lazy-load the HL Exchange SDK."""
        if self._exchange is None:
            from eth_account import Account
            from hyperliquid.exchange import Exchange
            from hyperliquid.utils import constants

            if not self.private_key:
                raise ValueError("private_key required for trading")
            acct = Account.from_key(self.private_key)
            base_url = (
                constants.TESTNET_API_URL if self.testnet else constants.MAINNET_API_URL
            )
            self._exchange = Exchange(acct, base_url)
        return self._exchange

    @property
    def _hl_info(self) -> Any:
        """Lazy-load the HL Info SDK."""
        if self._info is None:
            from hyperliquid.info import Info
            from hyperliquid.utils import constants

            base_url = (
                constants.TESTNET_API_URL if self.testnet else constants.MAINNET_API_URL
            )
            self._info = Info(base_url, skip_ws=True)
        return self._info

    def get_price(self) -> MarketPrice:
        """Get current UBTC/USDC price from Hyperliquid."""
        mids = self._hl_info.all_mids()
        price_str = mids.get(UBTC_PAIR) or mids.get("BTC")
        if price_str is None:
            raise ValueError(f"UBTC pair {UBTC_PAIR} not found in HL mids")
        price = Decimal(str(price_str))
        spread = price * Decimal("0.0005")
        return MarketPrice(
            symbol="UBTC/USDC",
            bid=price - spread,
            ask=price + spread,
            last=price,
        )

    def get_balances(self) -> dict[str, Balance]:
        """Get spot balances from Hyperliquid."""
        from eth_account import Account

        addr = self.wallet_address
        if not addr and self.private_key:
            addr = Account.from_key(self.private_key).address
        if not addr:
            raise ValueError("Wallet address required to query balances")

        state = self._hl_info.spot_user_state(addr)
        balances: dict[str, Balance] = {}
        for item in state.get("balances", []):
            asset = item.get("coin", "UNKNOWN")
            total = Decimal(str(item.get("total", "0")))
            hold = Decimal(str(item.get("hold", "0")))
            balances[asset] = Balance(
                asset=asset,
                free=total - hold,
                locked=hold,
            )
        return balances

    def market_buy(self, quote_amount: Decimal) -> OrderResult:
        """
        Buy UBTC with USDC at market price (GTC limit at 1% above mid).

        Args:
            quote_amount: USDC amount to spend.

        Returns:
            OrderResult with fill details.
        """
        price_data = self.get_price()
        price = price_data.last

        btc_size = round(float(quote_amount / price), UBTC_SZ_DECIMALS)
        if btc_size <= 0:
            return OrderResult(
                order_id="",
                status="failed",
                filled_qty=Decimal("0"),
                avg_fill_price=Decimal("0"),
                fee=Decimal("0"),
                raw={"error": f"Order size too small: {btc_size} UBTC"},
            )

        limit_price = round(float(price) * 1.01, UBTC_PX_DECIMALS)
        result = self._hl_exchange.order(
            UBTC_PAIR, True, btc_size, limit_price, {"limit": {"tif": "Gtc"}}
        )

        return self._parse_order_result(result, price)

    def market_sell(self, base_amount: Decimal) -> OrderResult:
        """
        Sell UBTC for USDC at market price (GTC limit at 1% below mid).

        Args:
            base_amount: UBTC amount to sell.

        Returns:
            OrderResult with fill details.
        """
        price_data = self.get_price()
        price = price_data.last

        btc_size = round(float(base_amount), UBTC_SZ_DECIMALS)
        if btc_size <= 0:
            return OrderResult(
                order_id="",
                status="failed",
                filled_qty=Decimal("0"),
                avg_fill_price=Decimal("0"),
                fee=Decimal("0"),
                raw={"error": f"Sell size too small: {btc_size} UBTC"},
            )

        limit_price = round(float(price) * 0.99, UBTC_PX_DECIMALS)
        result = self._hl_exchange.order(
            UBTC_PAIR, False, btc_size, limit_price, {"limit": {"tif": "Gtc"}}
        )

        return self._parse_order_result(result, price)

    def _parse_order_result(self, raw: dict[str, Any], ref_price: Decimal) -> OrderResult:
        """Parse HL order response into OrderResult."""
        if raw.get("status") != "ok":
            return OrderResult(
                order_id="",
                status="failed",
                filled_qty=Decimal("0"),
                avg_fill_price=Decimal("0"),
                fee=Decimal("0"),
                raw=raw,
            )

        statuses = raw.get("response", {}).get("data", {}).get("statuses", [])
        if not statuses:
            return OrderResult(
                order_id=str(uuid.uuid4()),
                status="unknown",
                filled_qty=Decimal("0"),
                avg_fill_price=ref_price,
                fee=Decimal("0"),
                raw=raw,
            )

        fill_info = statuses[0]
        if "filled" in fill_info:
            filled = fill_info["filled"]
            avg_px = Decimal(str(filled.get("avgPx", ref_price)))
            total_sz = Decimal(str(filled.get("totalSz", "0")))
            oid = str(filled.get("oid", uuid.uuid4()))
            fee = total_sz * avg_px * Decimal("0.001")
            return OrderResult(
                order_id=oid,
                status="filled",
                filled_qty=total_sz,
                avg_fill_price=avg_px,
                fee=fee,
                raw=raw,
            )
        elif "resting" in fill_info:
            oid = str(fill_info["resting"].get("oid", uuid.uuid4()))
            # Cancel resting order immediately
            try:
                self._hl_exchange.cancel(UBTC_PAIR, int(oid))
            except Exception:
                pass
            return OrderResult(
                order_id=oid,
                status="resting",
                filled_qty=Decimal("0"),
                avg_fill_price=ref_price,
                fee=Decimal("0"),
                raw=raw,
            )
        elif "error" in fill_info:
            return OrderResult(
                order_id="",
                status="failed",
                filled_qty=Decimal("0"),
                avg_fill_price=Decimal("0"),
                fee=Decimal("0"),
                raw=raw,
            )

        return OrderResult(
            order_id="",
            status="unknown",
            filled_qty=Decimal("0"),
            avg_fill_price=ref_price,
            fee=Decimal("0"),
            raw=raw,
        )

    def close(self) -> None:
        """Clean up HL client resources."""
        self._exchange = None
        self._info = None
