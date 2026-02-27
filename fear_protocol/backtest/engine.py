"""Backtesting engine — runs strategies against historical data."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Iterator

from fear_protocol.core.models import (
    ActionType,
    BacktestConfig,
    BacktestResult,
    BacktestTick,
    MarketContext,
    OrderResult,
)
from fear_protocol.core import math as fp_math
from fear_protocol.exchanges.mock import MockAdapter
from fear_protocol.strategies.base import AbstractStrategy

logger = logging.getLogger("fear_protocol.backtest")


class BacktestEngine:
    """
    Runs strategies against historical Fear & Greed and price data.

    Uses MockAdapter for deterministic order fills with configurable
    slippage and fees. The same code path as live trading — no special
    backtest mode means real bugs get caught.
    """

    def __init__(self, config: BacktestConfig, strategy: AbstractStrategy) -> None:
        """
        Initialize the backtest engine.

        Args:
            config: Backtest configuration (dates, capital, fees).
            strategy: Strategy instance to evaluate.
        """
        self.config = config
        self.strategy = strategy

    def _load_data(
        self,
    ) -> tuple[dict[str, int], dict[str, Decimal]]:
        """Load historical F&G and price data."""
        from fear_protocol.data.historical import HistoricalDataProvider

        provider = HistoricalDataProvider()
        fg_data = provider.get_fear_greed_history(
            self.config.start_date, self.config.end_date
        )
        price_data = provider.get_price_history(
            "BTCUSDT", self.config.start_date, self.config.end_date
        )
        return fg_data, price_data

    def _load_data_from_dicts(
        self,
        fg_data: dict[str, int],
        price_data: dict[str, Decimal],
    ) -> tuple[dict[str, int], dict[str, Decimal]]:
        """Use provided data directly (for testing without network calls)."""
        # Filter by date range
        filtered_fg = {
            d: v
            for d, v in fg_data.items()
            if self.config.start_date <= d <= self.config.end_date
        }
        filtered_prices = {
            d: v
            for d, v in price_data.items()
            if self.config.start_date <= d <= self.config.end_date
        }
        return filtered_fg, filtered_prices

    def run(
        self,
        fg_data: dict[str, int] | None = None,
        price_data: dict[str, Decimal] | None = None,
    ) -> BacktestResult:
        """
        Run the full backtest.

        Args:
            fg_data: Optional pre-loaded F&G data (skips network call).
            price_data: Optional pre-loaded price data (skips network call).

        Returns:
            Complete BacktestResult with metrics and trade log.
        """
        ticks = list(self.run_streaming(fg_data=fg_data, price_data=price_data))
        return self._compute_result(ticks)

    def run_streaming(
        self,
        fg_data: dict[str, int] | None = None,
        price_data: dict[str, Decimal] | None = None,
    ) -> Iterator[BacktestTick]:
        """
        Stream ticks for real-time progress display.

        Args:
            fg_data: Optional pre-loaded F&G data.
            price_data: Optional pre-loaded price data.

        Yields:
            BacktestTick for each day in the backtest period.
        """
        if fg_data is not None and price_data is not None:
            fg_hist, price_hist = self._load_data_from_dicts(fg_data, price_data)
        else:
            fg_hist, price_hist = self._load_data()

        # Merge dates: only days with both F&G and price data
        dates = sorted(set(fg_hist.keys()) & set(price_hist.keys()))
        if not dates:
            logger.warning("No overlapping data for backtest period")
            return

        mock = MockAdapter(
            initial_price=price_hist[dates[0]],
            fee_rate=self.config.fee_rate,
            slippage_rate=self.config.slippage_rate,
            initial_quote_balance=self.config.initial_capital,
        )

        open_positions: list[dict] = []
        total_invested = Decimal("0")

        for date in dates:
            price = price_hist[date]
            fg = fg_hist[date]
            mock.set_price(price)

            # Build portfolio value
            balances = mock.get_balances()
            base_held = balances["BTC"].total
            quote_held = balances["USDT"].total
            portfolio_value = quote_held + base_held * price

            # Build context
            ctx = MarketContext(
                timestamp=date,
                fear_greed=fg,
                fear_greed_label=_fg_label(fg),
                price=price,
                portfolio_value=portfolio_value,
                total_invested=total_invested,
                open_positions=open_positions,
            )

            # Strategy evaluation
            signal = self.strategy.evaluate(ctx)
            fill: OrderResult | None = None

            if signal.action == ActionType.BUY and signal.suggested_amount > 0:
                fill = mock.market_buy(signal.suggested_amount)
                if fill.status == "filled":
                    total_invested += signal.suggested_amount
                    open_positions.append({
                        "timestamp": date,
                        "entry_price": float(fill.avg_fill_price),
                        "btc_qty": float(fill.filled_qty),
                        "usd_amount": float(signal.suggested_amount),
                        "fg_at_entry": fg,
                        "status": "open",
                        "mode": "backtest",
                    })

            elif signal.action == ActionType.SELL and signal.suggested_amount > 0:
                sell_qty = signal.suggested_amount
                # Only sell what we have
                sell_qty = min(sell_qty, base_held)
                if sell_qty > Decimal("0.00001"):
                    fill = mock.market_sell(sell_qty)
                    if fill.status == "filled":
                        # Mark eligible positions as closed
                        sold_qty = fill.filled_qty
                        remaining = sold_qty
                        for pos in open_positions:
                            if pos["status"] != "open" or remaining <= 0:
                                continue
                            pos_qty = Decimal(str(pos["btc_qty"]))
                            if pos_qty <= remaining:
                                pos["status"] = "closed"
                                pos["exit_price"] = float(fill.avg_fill_price)
                                pos["exit_timestamp"] = date
                                pos["pnl_pct"] = (
                                    (float(fill.avg_fill_price) - pos["entry_price"])
                                    / pos["entry_price"]
                                    * 100
                                )
                                remaining -= pos_qty
                                total_invested -= Decimal(str(pos["usd_amount"]))
                            else:
                                break

            # Re-read balances post-fill
            balances = mock.get_balances()
            base_held = balances["BTC"].total
            quote_held = balances["USDT"].total
            portfolio_value = quote_held + base_held * price

            yield BacktestTick(
                date=date,
                price=price,
                fear_greed=fg,
                action=signal.action,
                signal=signal,
                fill=fill,
                portfolio_value=portfolio_value,
                cash=quote_held,
                base_held=base_held,
            )

    def _compute_result(self, ticks: list[BacktestTick]) -> BacktestResult:
        """Compute BacktestResult metrics from ticks."""
        if not ticks:
            return BacktestResult(
                config=self.config,
                ticks=[],
                trades=[],
                total_return_pct=0.0,
                annualized_return_pct=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                max_drawdown_pct=0.0,
                calmar_ratio=0.0,
                win_rate_pct=0.0,
                avg_win_pct=0.0,
                avg_loss_pct=0.0,
                profit_factor=0.0,
                total_trades=0,
                avg_hold_days=0.0,
                btc_hold_return_pct=0.0,
                alpha=0.0,
            )

        initial = float(self.config.initial_capital)
        final = float(ticks[-1].portfolio_value)
        total_return = (final - initial) / initial * 100

        # Equity curve for drawdown
        equity = [float(t.portfolio_value) for t in ticks]
        max_dd = fp_math.max_drawdown(equity)

        # Trade-level returns
        trades: list[dict] = []
        trade_returns: list[float] = []
        hold_durations: list[float] = []

        for tick in ticks:
            if tick.action == ActionType.SELL and tick.fill and tick.fill.status == "filled":
                # Find closed positions on this date
                pass

        # Collect closed positions from ticks via open_positions snapshots
        # We track trades differently — look at fills
        buy_fills = [
            t for t in ticks if t.action == ActionType.BUY and t.fill and t.fill.status == "filled"
        ]
        sell_fills = [
            t for t in ticks if t.action == ActionType.SELL and t.fill and t.fill.status == "filled"
        ]

        # Simple per-fill return computation
        for stk in sell_fills:
            # Approximate: compare sell price to avg buy price across all buys
            if buy_fills:
                avg_buy = float(
                    sum(t.fill.avg_fill_price for t in buy_fills if t.fill) / len(buy_fills)
                )
                pnl = (float(stk.fill.avg_fill_price) - avg_buy) / avg_buy * 100  # type: ignore[union-attr]
                trade_returns.append(pnl)
                trades.append({
                    "sell_date": stk.date,
                    "sell_price": float(stk.fill.avg_fill_price),  # type: ignore[union-attr]
                    "pnl_pct": round(pnl, 2),
                })

        # More accurate: collect from position data in ticks
        # Use ticks-embedded position data
        closed_positions: list[dict] = []
        seen_exits: set[str] = set()
        for tick in ticks:
            for pos in tick.signal.metadata.get("_closed_positions", []):
                key = f"{pos.get('timestamp', '')}_{pos.get('exit_timestamp', '')}"
                if key not in seen_exits:
                    seen_exits.add(key)
                    closed_positions.append(pos)

        if closed_positions:
            trade_returns = [p["pnl_pct"] for p in closed_positions if p.get("pnl_pct") is not None]
            trades = closed_positions
            hold_durations = []
            for p in closed_positions:
                try:
                    entry = datetime.fromisoformat(p["timestamp"])
                    exit_dt = datetime.fromisoformat(p["exit_timestamp"])
                    hold_durations.append((exit_dt - entry).days)
                except (KeyError, ValueError):
                    pass

        days = max(1, (
            datetime.strptime(ticks[-1].date, "%Y-%m-%d")
            - datetime.strptime(ticks[0].date, "%Y-%m-%d")
        ).days)

        ann_return = fp_math.annualized_return(total_return, days)
        sharpe = fp_math.sharpe_ratio(trade_returns) if trade_returns else 0.0
        sortino = fp_math.sortino_ratio(trade_returns) if trade_returns else 0.0
        calmar = fp_math.calmar_ratio(ann_return, max_dd)

        wins = [r for r in trade_returns if r > 0]
        losses = [r for r in trade_returns if r < 0]
        win_rate = len(wins) / len(trade_returns) * 100 if trade_returns else 0.0
        avg_win = sum(wins) / len(wins) if wins else 0.0
        avg_loss = sum(losses) / len(losses) if losses else 0.0
        pf = fp_math.profit_factor(wins, losses)
        avg_hold = sum(hold_durations) / len(hold_durations) if hold_durations else 0.0

        # BTC buy-and-hold benchmark
        first_price = float(ticks[0].price)
        last_price = float(ticks[-1].price)
        btc_hold = (last_price - first_price) / first_price * 100

        return BacktestResult(
            config=self.config,
            ticks=ticks,
            trades=trades,
            total_return_pct=total_return,
            annualized_return_pct=ann_return,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown_pct=max_dd,
            calmar_ratio=calmar,
            win_rate_pct=win_rate,
            avg_win_pct=avg_win,
            avg_loss_pct=avg_loss,
            profit_factor=pf,
            total_trades=len(buy_fills),
            avg_hold_days=avg_hold,
            btc_hold_return_pct=btc_hold,
            alpha=total_return - btc_hold,
        )


def _fg_label(fg: int) -> str:
    """Return human-readable label for a Fear & Greed value."""
    if fg <= 20:
        return "Extreme Fear"
    elif fg <= 40:
        return "Fear"
    elif fg <= 60:
        return "Neutral"
    elif fg <= 80:
        return "Greed"
    else:
        return "Extreme Greed"
