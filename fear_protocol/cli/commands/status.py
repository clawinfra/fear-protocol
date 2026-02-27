"""CLI command: fear-protocol status."""
from __future__ import annotations

import json

import typer

app = typer.Typer(help="Show current positions and P&L.")


@app.callback(invoke_without_command=True)
def status_cmd(
    exchange: str = typer.Option("paper", help="Exchange"),
    mode: str = typer.Option("paper", help="Mode: paper|live"),
    output_json: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Show current positions, balances, and P&L."""
    from fear_protocol.cli.output import print_status
    from fear_protocol.state.manager import StateManager
    from fear_protocol.data.price import BinancePriceProvider

    manager = StateManager(exchange=exchange, mode=mode)
    state = manager.load()

    try:
        price_provider = BinancePriceProvider()
        price = float(price_provider.get_price())
    except Exception:
        price = 0.0

    summary = manager.get_summary(state, price)

    if output_json:
        typer.echo(json.dumps(summary, indent=2))
    else:
        print_status(summary)
