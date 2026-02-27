"""CLI command: fear-protocol backtest."""
from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(help="Backtest a strategy on historical data.")


@app.callback(invoke_without_command=True)
def backtest_cmd(
    strategy: str = typer.Option("fear-greed-dca", help="Strategy name"),
    start: str = typer.Option("2020-01-01", help="Start date YYYY-MM-DD"),
    end: str = typer.Option(datetime.now().strftime("%Y-%m-%d"), help="End date YYYY-MM-DD"),
    capital: float = typer.Option(10000.0, help="Starting capital in USD"),
    buy_threshold: int = typer.Option(20, help="F&G buy threshold"),
    hold_days: int = typer.Option(120, help="Hold period in days"),
    fee: float = typer.Option(0.001, help="Fee rate"),
    slippage: float = typer.Option(0.001, help="Slippage rate"),
    output: Optional[Path] = typer.Option(None, help="Save JSON results to file"),
    output_json: bool = typer.Option(False, "--json", help="Output JSON to stdout"),
) -> None:
    """Backtest a strategy on historical data."""
    from fear_protocol.backtest.engine import BacktestEngine
    from fear_protocol.backtest.report import BacktestReport
    from fear_protocol.core.models import BacktestConfig
    from fear_protocol.strategies import get_strategy

    strategy_params = {
        "buy_threshold": buy_threshold,
        "hold_days": hold_days,
    }

    strat = get_strategy(strategy, strategy_params)
    config = BacktestConfig(
        strategy_name=strategy,
        start_date=start,
        end_date=end,
        initial_capital=Decimal(str(capital)),
        fee_rate=Decimal(str(fee)),
        slippage_rate=Decimal(str(slippage)),
        strategy_params=strategy_params,
    )

    typer.echo(f"Running backtest: {strategy} | {start} → {end} | capital=${capital:,.0f}")

    engine = BacktestEngine(config=config, strategy=strat)
    result = engine.run()
    report = BacktestReport(result)

    if output_json:
        typer.echo(json.dumps(result.to_dict(), indent=2))
    elif output:
        report.to_json(output)
        typer.echo(f"Results saved to {output}")
    else:
        report.print_summary()
