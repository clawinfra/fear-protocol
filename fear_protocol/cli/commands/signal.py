"""CLI command: fear-protocol signal."""
from __future__ import annotations

import json
import time
from typing import Optional

import typer

app = typer.Typer(help="Check current Fear & Greed signal.")


@app.callback(invoke_without_command=True)
def signal_cmd(
    threshold: int = typer.Option(20, help="Buy signal threshold (F&G ≤ this = BUY)"),
    output_json: bool = typer.Option(False, "--json", help="Output JSON"),
    watch: bool = typer.Option(False, help="Refresh on interval"),
    interval: int = typer.Option(300, help="Watch interval in seconds"),
) -> None:
    """Check current Fear & Greed index and signal."""
    from fear_protocol.data.fear_greed import FearGreedProvider
    from fear_protocol.data.price import BinancePriceProvider
    from fear_protocol.cli.output import print_signal

    def _fetch_and_print() -> None:
        fg_provider = FearGreedProvider()
        price_provider = BinancePriceProvider()

        fg = fg_provider.get_current()
        try:
            price = float(price_provider.get_price())
        except Exception:
            price = 0.0

        action = "BUY" if fg["value"] <= threshold else "HOLD"
        result = {
            "timestamp": fg["timestamp"],
            "action": action,
            "confidence": max(0.5, (threshold - fg["value"]) / threshold + 0.5) if action == "BUY" else 1.0,
            "fear_greed": fg["value"],
            "fear_greed_label": fg["label"],
            "price": price,
            "reason": f"F&G={fg['value']} {'≤' if action == 'BUY' else '>'} {threshold}",
            "suggested_amount": 500.0 if action == "BUY" else 0.0,
            "strategy": "fear-greed-dca",
            "metadata": {"threshold": threshold},
        }

        if output_json:
            typer.echo(json.dumps(result, indent=2))
        else:
            print_signal(result)

    if watch:
        while True:
            _fetch_and_print()
            time.sleep(interval)
    else:
        _fetch_and_print()
