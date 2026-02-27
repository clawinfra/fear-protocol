"""Abstract strategy interface."""
from __future__ import annotations

from abc import ABC, abstractmethod

from fear_protocol.core.models import MarketContext, OrderResult, StrategySignal


class AbstractStrategy(ABC):
    """
    Strategy interface. Implement this to create a new strategy.

    A strategy is a pure function: MarketContext → StrategySignal.
    It must NOT have side effects. Execution is handled by the engine.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name, e.g. 'fear-greed-dca'."""

    @property
    @abstractmethod
    def description(self) -> str:
        """One-line description of the strategy."""

    @abstractmethod
    def evaluate(self, ctx: MarketContext) -> StrategySignal:
        """
        Evaluate market context and return a signal.

        Must be deterministic for the same input (enables backtesting).

        Args:
            ctx: Current market context snapshot.

        Returns:
            StrategySignal with action, confidence, reason, and amount.
        """

    def on_fill(self, order_result: OrderResult, ctx: MarketContext) -> None:
        """
        Called after an order is filled. Override for stateful strategies.

        Args:
            order_result: Result of the executed order.
            ctx: Market context at the time of fill.
        """

    def validate_config(self) -> None:
        """Validate strategy config. Raise ValueError if invalid."""
