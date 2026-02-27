"""fear-protocol CLI entrypoint."""
from __future__ import annotations

import typer

from fear_protocol.cli.commands.backtest import app as backtest_app
from fear_protocol.cli.commands.run import app as run_app
from fear_protocol.cli.commands.signal import app as signal_app
from fear_protocol.cli.commands.status import app as status_app

app = typer.Typer(
    name="fear-protocol",
    help="Exchange-agnostic sentiment-driven DCA framework.",
    no_args_is_help=True,
)

app.add_typer(signal_app, name="signal")
app.add_typer(run_app, name="run")
app.add_typer(backtest_app, name="backtest")
app.add_typer(status_app, name="status")


@app.command()
def version() -> None:
    """Show fear-protocol version."""
    typer.echo("fear-protocol v0.1.0")


if __name__ == "__main__":
    app()
