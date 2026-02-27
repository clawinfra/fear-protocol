"""CLI command: fear-protocol run."""
from __future__ import annotations

import json
from typing import Optional

import typer

app = typer.Typer(help="Run a DCA strategy.")


@app.callback(invoke_without_command=True)
def run_cmd(
    strategy: str = typer.Option("fear-greed-dca", help="Strategy name"),
    exchange: str = typer.Option("paper", help="Exchange adapter"),
    mode: str = typer.Option("dry-run", help="Execution mode: dry-run|paper|live"),
    buy_threshold: int = typer.Option(20, help="F&G buy threshold"),
    sell_threshold: int = typer.Option(50, help="F&G sell threshold"),
    hold_days: int = typer.Option(120, help="Minimum hold days"),
    dca_amount: float = typer.Option(500.0, help="USD per DCA buy"),
    max_capital: float = typer.Option(5000.0, help="Maximum capital"),
    testnet: bool = typer.Option(False, help="Use exchange testnet"),
    output_json: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Run the DCA strategy once (evaluate + optionally execute)."""
    from fear_protocol.agent.api import FearProtocolAgent
    from fear_protocol.cli.output import print_run_result

    params = {
        "buy_threshold": buy_threshold,
        "sell_threshold": sell_threshold,
        "hold_days": hold_days,
        "dca_amount_usd": dca_amount,
        "max_capital_usd": max_capital,
    }

    agent = FearProtocolAgent(
        strategy=strategy,
        exchange=exchange,
        mode=mode,
        strategy_params=params,
        testnet=testnet,
    )

    # Get current state if paper/live
    result = agent.run_once()

    if output_json:
        typer.echo(json.dumps(result, indent=2))
    else:
        print_run_result(result)
