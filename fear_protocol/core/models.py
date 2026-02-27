"""Core domain models for fear-protocol."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any


class ActionType(str, Enum):
    """Possible strategy actions."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class MarketContext:
    """Input snapshot provided to strategies on each evaluation tick."""

    timestamp: str
    fear_greed: int
    fear_greed_label: str
    price: Decimal
    portfolio_value: Decimal
    total_invested: Decimal
    open_positions: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class StrategySignal:
    """Output of a strategy evaluation."""

    action: ActionType
    confidence: float  # 0.0–1.0
    reason: str  # human-readable explanation
    suggested_amount: Decimal  # quote amount for BUY, base amount for SELL
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OrderResult:
    """Result of an order placement."""

    order_id: str
    status: str  # "filled" | "partial" | "resting" | "failed"
    filled_qty: Decimal
    avg_fill_price: Decimal
    fee: Decimal
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class Balance:
    """Asset balance on an exchange."""

    asset: str
    free: Decimal
    locked: Decimal

    @property
    def total(self) -> Decimal:
        """Total balance (free + locked)."""
        return self.free + self.locked


@dataclass
class MarketPrice:
    """Current market price data for a trading pair."""

    symbol: str
    bid: Decimal
    ask: Decimal
    last: Decimal

    @property
    def mid(self) -> Decimal:
        """Mid price between bid and ask."""
        return (self.bid + self.ask) / 2


@dataclass
class Position:
    """An open or closed trading position."""

    timestamp: str
    entry_price: Decimal
    base_qty: Decimal
    quote_amount: Decimal
    fg_at_entry: int
    status: str  # "open" | "closed"
    mode: str
    order_id: str | None = None
    exit_price: Decimal | None = None
    exit_timestamp: str | None = None
    pnl_pct: float | None = None

    def unrealized_pnl(self, current_price: Decimal) -> Decimal:
        """Calculate unrealized P&L at current price."""
        if self.status != "open":
            return Decimal("0")
        current_value = self.base_qty * current_price
        return current_value - self.quote_amount

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "timestamp": self.timestamp,
            "entry_price": float(self.entry_price),
            "btc_qty": float(self.base_qty),
            "usd_amount": float(self.quote_amount),
            "fg_at_entry": self.fg_at_entry,
            "status": self.status,
            "mode": self.mode,
            "hl_order_id": self.order_id,
            "exit_price": float(self.exit_price) if self.exit_price else None,
            "exit_timestamp": self.exit_timestamp,
            "pnl_pct": self.pnl_pct,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Position":
        """Deserialize from dict."""
        return cls(
            timestamp=data["timestamp"],
            entry_price=Decimal(str(data["entry_price"])),
            base_qty=Decimal(str(data.get("btc_qty", data.get("base_qty", 0)))),
            quote_amount=Decimal(str(data.get("usd_amount", data.get("quote_amount", 0)))),
            fg_at_entry=data["fg_at_entry"],
            status=data["status"],
            mode=data.get("mode", "unknown"),
            order_id=data.get("hl_order_id") or data.get("order_id"),
            exit_price=Decimal(str(data["exit_price"])) if data.get("exit_price") else None,
            exit_timestamp=data.get("exit_timestamp"),
            pnl_pct=data.get("pnl_pct"),
        )


@dataclass
class BacktestConfig:
    """Configuration for a backtest run."""

    strategy_name: str
    start_date: str  # "2018-01-01"
    end_date: str  # "2024-12-31"
    initial_capital: Decimal
    fee_rate: Decimal = Decimal("0.001")
    slippage_rate: Decimal = Decimal("0.001")
    data_source: str = "binance"
    fear_greed_source: str = "alternative.me"
    strategy_params: dict[str, Any] = field(default_factory=dict)


@dataclass
class BacktestTick:
    """A single day's data point in a backtest run."""

    date: str
    price: Decimal
    fear_greed: int
    action: ActionType
    signal: StrategySignal
    fill: OrderResult | None
    portfolio_value: Decimal
    cash: Decimal
    base_held: Decimal


@dataclass
class BacktestResult:
    """Complete results from a backtest run."""

    config: BacktestConfig
    ticks: list[BacktestTick]
    trades: list[dict[str, Any]]

    # Core metrics
    total_return_pct: float
    annualized_return_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    calmar_ratio: float
    win_rate_pct: float
    avg_win_pct: float
    avg_loss_pct: float
    profit_factor: float
    total_trades: int
    avg_hold_days: float

    # Benchmark
    btc_hold_return_pct: float
    alpha: float

    def to_dict(self) -> dict[str, Any]:
        """Serialize result to JSON-compatible dict."""
        return {
            "strategy": self.config.strategy_name,
            "start_date": self.config.start_date,
            "end_date": self.config.end_date,
            "total_return_pct": round(self.total_return_pct, 2),
            "annualized_return_pct": round(self.annualized_return_pct, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 2),
            "sortino_ratio": round(self.sortino_ratio, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "calmar_ratio": round(self.calmar_ratio, 2),
            "win_rate_pct": round(self.win_rate_pct, 1),
            "avg_win_pct": round(self.avg_win_pct, 2),
            "avg_loss_pct": round(self.avg_loss_pct, 2),
            "profit_factor": round(self.profit_factor, 2),
            "total_trades": self.total_trades,
            "avg_hold_days": round(self.avg_hold_days, 1),
            "btc_hold_return_pct": round(self.btc_hold_return_pct, 2),
            "alpha": round(self.alpha, 2),
            "trades": self.trades,
        }
