"""FearGreedDCA strategy — ported and enhanced from FearHarvester."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from fear_protocol.core.models import ActionType, MarketContext, StrategySignal
from fear_protocol.strategies.base import AbstractStrategy


@dataclass
class FearGreedDCAConfig:
    """Configuration for the FearGreedDCA strategy."""

    buy_threshold: int = 20
    """F&G value at or below which to trigger a BUY. Default: 20 (Extreme Fear)."""

    sell_threshold: int = 50
    """F&G value at or above which to consider selling. Default: 50 (Neutral)."""

    hold_days: int = 120
    """Minimum days to hold a position before selling. Default: 120."""

    dca_amount_usd: Decimal = Decimal("500")
    """USD amount per DCA buy. Default: $500."""

    max_capital_usd: Decimal = Decimal("5000")
    """Maximum total capital to deploy. Default: $5,000."""

    kelly_fraction: float = 0.0
    """Kelly sizing fraction. 0.0 = use fixed dca_amount_usd."""

    def validate(self) -> None:
        """Validate configuration values."""
        if not 0 <= self.buy_threshold <= 100:
            raise ValueError(f"buy_threshold must be 0-100, got {self.buy_threshold}")
        if not 0 <= self.sell_threshold <= 100:
            raise ValueError(f"sell_threshold must be 0-100, got {self.sell_threshold}")
        if self.buy_threshold >= self.sell_threshold:
            raise ValueError(
                f"buy_threshold ({self.buy_threshold}) must be < sell_threshold ({self.sell_threshold})"
            )
        if self.hold_days < 1:
            raise ValueError(f"hold_days must be >= 1, got {self.hold_days}")
        if self.dca_amount_usd <= 0:
            raise ValueError(f"dca_amount_usd must be > 0, got {self.dca_amount_usd}")
        if self.max_capital_usd <= 0:
            raise ValueError(f"max_capital_usd must be > 0, got {self.max_capital_usd}")


class FearGreedDCAStrategy(AbstractStrategy):
    """
    The original FearHarvester strategy, now with full strategy interface.

    DCA when F&G ≤ buy_threshold.
    Rebalance when F&G ≥ sell_threshold AND hold_days have elapsed.
    Backtested Sharpe 2.01 on 2018-2024 data.
    """

    @property
    def name(self) -> str:
        """Strategy identifier."""
        return "fear-greed-dca"

    @property
    def description(self) -> str:
        """Strategy description."""
        return "DCA on extreme fear (F&G ≤ threshold), hold minimum N days, exit on recovery"

    def __init__(self, config: FearGreedDCAConfig | None = None) -> None:
        """
        Initialize the strategy.

        Args:
            config: Strategy configuration. Defaults to standard parameters.
        """
        self.config = config or FearGreedDCAConfig()

    def validate_config(self) -> None:
        """Validate the strategy configuration."""
        self.config.validate()

    def evaluate(self, ctx: MarketContext) -> StrategySignal:
        """
        Evaluate market context and return a trading signal.

        Logic:
        1. If F&G ≤ buy_threshold and capital available → BUY
        2. If F&G ≥ sell_threshold and eligible positions → SELL
        3. Otherwise → HOLD

        Args:
            ctx: Current market snapshot.

        Returns:
            StrategySignal with action, confidence, reason, and suggested amount.
        """
        cfg = self.config
        fg = ctx.fear_greed

        # BUY signal: extreme fear and capital available
        if fg <= cfg.buy_threshold:
            if ctx.total_invested < cfg.max_capital_usd:
                return StrategySignal(
                    action=ActionType.BUY,
                    confidence=self._fear_confidence(fg),
                    reason=f"F&G={fg} ≤ {cfg.buy_threshold} (Extreme Fear)",
                    suggested_amount=cfg.dca_amount_usd,
                    metadata={
                        "fg": fg,
                        "threshold": cfg.buy_threshold,
                        "total_invested": float(ctx.total_invested),
                        "max_capital": float(cfg.max_capital_usd),
                    },
                )
            else:
                return StrategySignal(
                    action=ActionType.HOLD,
                    confidence=1.0,
                    reason=f"F&G={fg} — extreme fear but max capital reached (${float(ctx.total_invested):,.0f})",
                    suggested_amount=Decimal("0"),
                    metadata={"fg": fg, "max_capital_reached": True},
                )

        # SELL signal: recovery + hold period elapsed
        if fg >= cfg.sell_threshold:
            eligible = self._get_eligible_positions(ctx)
            if eligible:
                total_qty = Decimal(str(sum(
                    p.get("btc_qty", p.get("base_qty", 0)) for p in eligible
                )))
                return StrategySignal(
                    action=ActionType.SELL,
                    confidence=0.8,
                    reason=(
                        f"F&G={fg} ≥ {cfg.sell_threshold} (Recovery), "
                        f"{len(eligible)} position(s) past {cfg.hold_days}d hold"
                    ),
                    suggested_amount=total_qty,
                    metadata={
                        "fg": fg,
                        "eligible_positions": len(eligible),
                        "sell_threshold": cfg.sell_threshold,
                    },
                )

        # HOLD: waiting for signal
        return StrategySignal(
            action=ActionType.HOLD,
            confidence=1.0,
            reason=f"F&G={fg} in neutral zone (buy≤{cfg.buy_threshold}, sell≥{cfg.sell_threshold})",
            suggested_amount=Decimal("0"),
            metadata={"fg": fg},
        )

    def _fear_confidence(self, fg: int) -> float:
        """
        Calculate confidence based on fear depth.

        Higher confidence at lower F&G (deeper fear = stronger signal).

        Args:
            fg: Current F&G value.

        Returns:
            Confidence float between 0.5 and 1.0.
        """
        threshold = self.config.buy_threshold
        if threshold == 0:
            return 1.0
        # Linear scaling: fg=0 → 1.0, fg=threshold → 0.5
        confidence = max(0.5, min(1.0, (threshold - fg) / threshold + 0.5))
        return confidence

    def _get_eligible_positions(self, ctx: MarketContext) -> list[dict[str, Any]]:
        """
        Return positions that have passed the minimum hold period.

        Args:
            ctx: Market context with open positions.

        Returns:
            List of position dicts eligible for selling.
        """
        now = datetime.now()
        eligible = []
        for pos in ctx.open_positions:
            if pos.get("status") != "open":
                continue
            try:
                entry = datetime.fromisoformat(pos["timestamp"])
            except (KeyError, ValueError):
                continue
            days_held = (now - entry).days
            if days_held >= self.config.hold_days:
                eligible.append(pos)
        return eligible

    @classmethod
    def from_dict(cls, params: dict[str, Any]) -> "FearGreedDCAStrategy":
        """
        Create strategy from a parameter dict.

        Args:
            params: Dict with optional keys: buy_threshold, sell_threshold,
                    hold_days, dca_amount_usd, max_capital_usd, kelly_fraction.

        Returns:
            Configured FearGreedDCAStrategy.
        """
        config = FearGreedDCAConfig(
            buy_threshold=params.get("buy_threshold", 20),
            sell_threshold=params.get("sell_threshold", 50),
            hold_days=params.get("hold_days", 120),
            dca_amount_usd=Decimal(str(params.get("dca_amount_usd", 500))),
            max_capital_usd=Decimal(str(params.get("max_capital_usd", 5000))),
            kelly_fraction=params.get("kelly_fraction", 0.0),
        )
        return cls(config=config)
