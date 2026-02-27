"""FearProtocolAgent — high-level agent-friendly API."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from fear_protocol.agent.schemas import ExecuteResultSchema, RunConfigSchema, SignalSchema
from fear_protocol.core.models import ActionType, BacktestConfig, MarketContext
from fear_protocol.data.fear_greed import FearGreedProvider
from fear_protocol.data.price import BinancePriceProvider
from fear_protocol.strategies import get_strategy


class FearProtocolAgent:
    """
    High-level API for agent integration.

    Designed for use in EvoClaw/OpenClaw agents — clean JSON in/out,
    no subprocess overhead, fully typed.
    """

    def __init__(
        self,
        strategy: str = "fear-greed-dca",
        exchange: str = "paper",
        mode: str = "dry-run",
        strategy_params: dict[str, Any] | None = None,
        testnet: bool = False,
    ) -> None:
        """
        Initialize the agent.

        Args:
            strategy: Strategy name.
            exchange: Exchange adapter name.
            mode: Execution mode ('dry-run', 'paper', 'live').
            strategy_params: Optional strategy configuration.
            testnet: Use exchange testnet.
        """
        self.strategy_name = strategy
        self.exchange_name = exchange
        self.mode = mode
        self.strategy_params = strategy_params or {}
        self.testnet = testnet
        self._strategy = get_strategy(strategy, strategy_params)

    def get_signal(self) -> dict[str, Any]:
        """
        Get current market signal without executing.

        Returns:
            SignalSchema dict with action, confidence, F&G, price, etc.
        """
        fg_provider = FearGreedProvider()
        price_provider = BinancePriceProvider()

        fg = fg_provider.get_current()
        price = price_provider.get_price()

        ctx = MarketContext(
            timestamp=datetime.now().isoformat(),
            fear_greed=fg["value"],
            fear_greed_label=fg["label"],
            price=price,
            portfolio_value=price,
            total_invested=Decimal("0"),
            open_positions=[],
        )

        signal = self._strategy.evaluate(ctx)

        schema = SignalSchema(
            timestamp=ctx.timestamp,
            action=signal.action.value,
            confidence=signal.confidence,
            fear_greed=fg["value"],
            fear_greed_label=fg["label"],
            price=float(price),
            reason=signal.reason,
            suggested_amount=float(signal.suggested_amount),
            strategy=self.strategy_name,
            metadata=signal.metadata,
        )
        return schema.model_dump()

    def run_once(self, state_summary: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Run one strategy tick (evaluate + optionally execute).

        Args:
            state_summary: Optional current position state for context.

        Returns:
            ExecuteResultSchema dict.
        """
        fg_provider = FearGreedProvider()
        price_provider = BinancePriceProvider()

        fg = fg_provider.get_current()
        price = price_provider.get_price()

        total_invested = Decimal(str(state_summary.get("total_invested", 0))) if state_summary else Decimal("0")
        open_positions = state_summary.get("open_positions", []) if state_summary else []

        ctx = MarketContext(
            timestamp=datetime.now().isoformat(),
            fear_greed=fg["value"],
            fear_greed_label=fg["label"],
            price=price,
            portfolio_value=price + total_invested,
            total_invested=total_invested,
            open_positions=open_positions,
        )

        signal = self._strategy.evaluate(ctx)

        is_dry_run = self.mode == "dry-run"

        if signal.action == ActionType.HOLD or is_dry_run:
            return ExecuteResultSchema(
                timestamp=ctx.timestamp,
                action=signal.action.value,
                success=True,
                error=None,
                dry_run=is_dry_run,
                mode=self.mode,
            ).model_dump()

        # Execute via adapter
        from fear_protocol.exchanges import get_adapter

        adapter = get_adapter(self.exchange_name)
        try:
            if signal.action == ActionType.BUY:
                fill = adapter.market_buy(signal.suggested_amount)
            else:
                fill = adapter.market_sell(signal.suggested_amount)

            from fear_protocol.agent.schemas import OrderFillSchema

            return ExecuteResultSchema(
                timestamp=ctx.timestamp,
                action=signal.action.value,
                success=fill.status == "filled",
                fill=OrderFillSchema(
                    order_id=fill.order_id,
                    status=fill.status,
                    filled_qty=float(fill.filled_qty),
                    avg_fill_price=float(fill.avg_fill_price),
                    fee=float(fill.fee),
                ),
                dry_run=False,
                mode=self.mode,
            ).model_dump()
        except Exception as e:
            return ExecuteResultSchema(
                timestamp=ctx.timestamp,
                action=signal.action.value,
                success=False,
                error=str(e),
                dry_run=False,
                mode=self.mode,
            ).model_dump()
        finally:
            adapter.close()

    def backtest(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Run a backtest and return results.

        Args:
            request: BacktestRequestSchema-compatible dict.

        Returns:
            BacktestResult dict.
        """
        from decimal import Decimal

        from fear_protocol.agent.schemas import BacktestRequestSchema
        from fear_protocol.backtest.engine import BacktestEngine

        req = BacktestRequestSchema(**request)
        strategy = get_strategy(req.strategy, req.strategy_params)
        config = BacktestConfig(
            strategy_name=req.strategy,
            start_date=req.start_date,
            end_date=req.end_date,
            initial_capital=Decimal(str(req.initial_capital)),
            fee_rate=Decimal(str(req.fee_rate)),
            slippage_rate=Decimal(str(req.slippage_rate)),
        )
        engine = BacktestEngine(config=config, strategy=strategy)
        result = engine.run()
        return result.to_dict()

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "FearProtocolAgent":
        """
        Create agent from config dict (RunConfigSchema-compatible).

        Args:
            config: Configuration dict.

        Returns:
            Configured FearProtocolAgent.
        """
        req = RunConfigSchema(**config)
        return cls(
            strategy=req.strategy,
            exchange=req.exchange,
            mode=req.mode,
            strategy_params=req.strategy_params,
            testnet=req.testnet,
        )
