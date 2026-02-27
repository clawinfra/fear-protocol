"""MomentumDCA strategy — DCA after consecutive red days + fear confirmation."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from fear_protocol.core.models import ActionType, MarketContext, StrategySignal
from fear_protocol.strategies.base import AbstractStrategy


@dataclass
class MomentumDCAConfig:
    """Configuration for the MomentumDCA strategy."""

    fear_threshold: int = 30
    """F&G must be at or below this value to activate momentum watch."""

    min_consecutive_down: int = 3
    """Trigger after N consecutive down days."""

    dca_amount_usd: Decimal = Decimal("500")
    """USD amount per DCA buy."""

    max_capital_usd: Decimal = Decimal("5000")
    """Maximum total capital to deploy."""

    hold_days: int = 60
    """Minimum hold period in days."""

    sell_threshold: int = 50
    """F&G at or above this → consider selling."""


class MomentumDCAStrategy(AbstractStrategy):
    """
    Combine price momentum with sentiment confirmation.

    Buy after N consecutive down days when F&G is also in fear territory.
    More selective than FearGreedDCA — waits for both conditions.
    """

    @property
    def name(self) -> str:
        """Strategy identifier."""
        return "momentum-dca"

    @property
    def description(self) -> str:
        """Strategy description."""
        return "DCA after N consecutive red days + fear confirmation"

    def __init__(self, config: MomentumDCAConfig | None = None) -> None:
        """
        Initialize the strategy.

        Args:
            config: Strategy configuration.
        """
        self.config = config or MomentumDCAConfig()
        self._price_history: list[Decimal] = []

    def update_price_history(self, price: Decimal) -> None:
        """
        Update internal price history (call once per tick in backtest).

        Args:
            price: Current day's closing price.
        """
        self._price_history.append(price)
        # Keep only last N+1 prices needed for consecutive down calculation
        max_needed = self.config.min_consecutive_down + 1
        if len(self._price_history) > max_needed:
            self._price_history = self._price_history[-max_needed:]

    def _count_consecutive_down(self) -> int:
        """Count consecutive declining days in price history."""
        prices = self._price_history
        if len(prices) < 2:
            return 0
        count = 0
        for i in range(len(prices) - 1, 0, -1):
            if prices[i] < prices[i - 1]:
                count += 1
            else:
                break
        return count

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
        self.update_price_history(ctx.price)
        consecutive_down = self._count_consecutive_down()

        # BUY: fear + consecutive down days
        if (
            fg <= cfg.fear_threshold
            and consecutive_down >= cfg.min_consecutive_down
            and ctx.total_invested < cfg.max_capital_usd
        ):
            confidence = min(1.0, 0.5 + consecutive_down * 0.1)
            return StrategySignal(
                action=ActionType.BUY,
                confidence=confidence,
                reason=(
                    f"F&G={fg} ≤ {cfg.fear_threshold} + {consecutive_down} consecutive down days"
                ),
                suggested_amount=cfg.dca_amount_usd,
                metadata={
                    "fg": fg,
                    "consecutive_down": consecutive_down,
                },
            )

        # SELL: recovery
        if fg >= cfg.sell_threshold:
            eligible = self._get_eligible_positions(ctx)
            if eligible:
                total_qty = Decimal(str(sum(
                    p.get("btc_qty", p.get("base_qty", 0)) for p in eligible
                )))
                return StrategySignal(
                    action=ActionType.SELL,
                    confidence=0.75,
                    reason=f"F&G={fg} ≥ {cfg.sell_threshold}, {len(eligible)} eligible positions",
                    suggested_amount=total_qty,
                    metadata={"fg": fg, "eligible_positions": len(eligible)},
                )

        return StrategySignal(
            action=ActionType.HOLD,
            confidence=1.0,
            reason=f"F&G={fg}, consecutive_down={consecutive_down} (need {cfg.min_consecutive_down})",
            suggested_amount=Decimal("0"),
            metadata={"fg": fg, "consecutive_down": consecutive_down},
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
    def from_dict(cls, params: dict[str, Any]) -> "MomentumDCAStrategy":
        """Create strategy from parameter dict."""
        config = MomentumDCAConfig(
            fear_threshold=params.get("fear_threshold", 30),
            min_consecutive_down=params.get("min_consecutive_down", 3),
            dca_amount_usd=Decimal(str(params.get("dca_amount_usd", 500))),
            max_capital_usd=Decimal(str(params.get("max_capital_usd", 5000))),
            hold_days=params.get("hold_days", 60),
            sell_threshold=params.get("sell_threshold", 50),
        )
        return cls(config=config)
