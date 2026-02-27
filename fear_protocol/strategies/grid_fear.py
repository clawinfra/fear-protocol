"""GridFear strategy — grid DCA with increasing size during fear periods."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from fear_protocol.core.models import ActionType, MarketContext, StrategySignal
from fear_protocol.strategies.base import AbstractStrategy


@dataclass
class GridFearConfig:
    """Configuration for the GridFear strategy."""

    fear_threshold: int = 25
    """F&G must be at or below this to activate grid buying."""

    grid_levels: int = 5
    """Number of grid levels."""

    grid_spacing_pct: float = 5.0
    """Percentage spacing between grid levels."""

    base_amount_usd: Decimal = Decimal("200")
    """Base amount per grid level in USD."""

    level_multiplier: float = 1.5
    """Amount multiplier per level below reference."""

    max_capital_usd: Decimal = Decimal("5000")
    """Maximum total capital."""

    sell_threshold: int = 50
    """F&G above this → consider selling."""

    hold_days: int = 90
    """Minimum hold period."""


class GridFearStrategy(AbstractStrategy):
    """
    Place grid buy orders at stepped price levels during fear periods.

    Heavier buys at lower levels (anti-martingale grid).
    Each grid level buys more than the previous as price drops.
    """

    @property
    def name(self) -> str:
        """Strategy identifier."""
        return "grid-fear"

    @property
    def description(self) -> str:
        """Strategy description."""
        return "Grid DCA with increasing size at lower fear levels"

    def __init__(self, config: GridFearConfig | None = None) -> None:
        """
        Initialize the strategy.

        Args:
            config: Strategy configuration.
        """
        self.config = config or GridFearConfig()
        self._reference_price: Decimal | None = None

    def _set_reference_if_needed(self, ctx: MarketContext) -> None:
        """Set reference price on first evaluation in fear zone."""
        if self._reference_price is None and ctx.fear_greed <= self.config.fear_threshold:
            self._reference_price = ctx.price

    def _get_grid_level(self, current_price: Decimal) -> int:
        """Determine which grid level the current price is at."""
        if self._reference_price is None:
            return 0
        drop_pct = float(
            (self._reference_price - current_price) / self._reference_price * 100
        )
        level = int(drop_pct / self.config.grid_spacing_pct)
        return min(level, self.config.grid_levels - 1)

    def _level_amount(self, level: int) -> Decimal:
        """Calculate buy amount for a given grid level."""
        multiplier = self.config.level_multiplier ** level
        return self.config.base_amount_usd * Decimal(str(multiplier))

    def evaluate(self, ctx: MarketContext) -> StrategySignal:
        """
        Evaluate market context and return a trading signal.

        Args:
            ctx: Current market snapshot.

        Returns:
            StrategySignal with action, confidence, reason, and suggested amount.
        """
        cfg = self.config
        fg = ctx.fear_greed

        # Fear zone: activate grid
        if fg <= cfg.fear_threshold and ctx.total_invested < cfg.max_capital_usd:
            self._set_reference_if_needed(ctx)
            level = self._get_grid_level(ctx.price)
            amount = self._level_amount(level)
            # Cap at remaining capital
            remaining = cfg.max_capital_usd - ctx.total_invested
            amount = min(amount, remaining)

            if amount > Decimal("10"):  # minimum order size
                return StrategySignal(
                    action=ActionType.BUY,
                    confidence=min(1.0, 0.5 + (cfg.fear_threshold - fg) / 50),
                    reason=f"F&G={fg} ≤ {cfg.fear_threshold} at grid level {level}",
                    suggested_amount=amount,
                    metadata={
                        "fg": fg,
                        "grid_level": level,
                        "reference_price": float(self._reference_price or ctx.price),
                    },
                )

        # Recovery: sell eligible positions
        if fg >= cfg.sell_threshold:
            eligible = self._get_eligible_positions(ctx)
            if eligible:
                total_qty = Decimal(str(sum(
                    p.get("btc_qty", p.get("base_qty", 0)) for p in eligible
                )))
                # Reset reference price on exit
                self._reference_price = None
                return StrategySignal(
                    action=ActionType.SELL,
                    confidence=0.8,
                    reason=f"F&G={fg} ≥ {cfg.sell_threshold}, grid exit",
                    suggested_amount=total_qty,
                    metadata={"fg": fg, "eligible_positions": len(eligible)},
                )

        return StrategySignal(
            action=ActionType.HOLD,
            confidence=1.0,
            reason=f"F&G={fg} outside grid zone",
            suggested_amount=Decimal("0"),
            metadata={"fg": fg},
        )

    def _get_eligible_positions(self, ctx: MarketContext) -> list[dict[str, Any]]:
        """Return positions past hold period."""
        from datetime import datetime

        now = datetime.now()
        eligible = []
        for pos in ctx.open_positions:
            if pos.get("status") != "open":
                continue
            try:
                entry = datetime.fromisoformat(pos["timestamp"])
                if (now - entry).days >= self.config.hold_days:
                    eligible.append(pos)
            except (KeyError, ValueError):
                continue
        return eligible

    @classmethod
    def from_dict(cls, params: dict[str, Any]) -> "GridFearStrategy":
        """Create strategy from parameter dict."""
        config = GridFearConfig(
            fear_threshold=params.get("fear_threshold", 25),
            grid_levels=params.get("grid_levels", 5),
            grid_spacing_pct=params.get("grid_spacing_pct", 5.0),
            base_amount_usd=Decimal(str(params.get("base_amount_usd", 200))),
            level_multiplier=params.get("level_multiplier", 1.5),
            max_capital_usd=Decimal(str(params.get("max_capital_usd", 5000))),
            sell_threshold=params.get("sell_threshold", 50),
            hold_days=params.get("hold_days", 90),
        )
        return cls(config=config)
