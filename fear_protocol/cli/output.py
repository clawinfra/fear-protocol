"""Rich terminal output utilities for fear-protocol CLI."""
from __future__ import annotations

from typing import Any

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
    from rich.text import Text

    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    console = None  # type: ignore[assignment]


def print_signal(signal: dict[str, Any]) -> None:
    """Print signal output to terminal."""
    action = signal["action"]
    fg = signal["fear_greed"]
    label = signal["fear_greed_label"]
    price = signal["price"]
    confidence = signal["confidence"]
    reason = signal["reason"]

    if HAS_RICH and console:
        action_color = {"BUY": "green", "SELL": "yellow", "HOLD": "blue"}[action]
        action_emoji = {"BUY": "🚨", "SELL": "💰", "HOLD": "✋"}[action]

        content = (
            f"[bold {action_color}]{action_emoji} {action}[/bold {action_color}]\n"
            f"F&G: {fg} ({label})\n"
            f"BTC: ${price:,.2f}\n"
            f"Confidence: {confidence:.0%}\n"
            f"Reason: {reason}"
        )
        if action == "BUY":
            content += f"\nSuggested: ${signal['suggested_amount']:,.0f}"

        console.print(Panel(content, title="Fear Protocol Signal", border_style=action_color))
    else:
        emoji = {"BUY": "🚨", "SELL": "💰", "HOLD": "✋"}[action]
        print(f"{emoji} {action} | F&G={fg} ({label}) | BTC=${price:,.2f}")
        print(f"   Confidence: {confidence:.0%} | {reason}")


def print_status(summary: dict[str, Any]) -> None:
    """Print position status to terminal."""
    if HAS_RICH and console:
        table = Table(title="Fear Protocol Status", box=box.ROUNDED)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="bold")

        table.add_row("Mode", summary.get("mode", "unknown"))
        table.add_row("Exchange", summary.get("exchange", "unknown"))
        table.add_row("Open Positions", str(summary.get("open_count", 0)))
        table.add_row("Closed Positions", str(summary.get("closed_count", 0)))

        if summary.get("open_count", 0) > 0:
            table.add_row("Total BTC", f"{summary.get('total_base', 0):.5f}")
            table.add_row("Avg Entry", f"${summary.get('avg_entry_price', 0):,.2f}")
            table.add_row("Current Value", f"${summary.get('current_value', 0):,.2f}")
            pnl = summary.get("unrealized_pnl", 0)
            pnl_pct = summary.get("unrealized_pnl_pct", 0)
            color = "green" if pnl >= 0 else "red"
            table.add_row(
                "Unrealized P&L",
                f"[{color}]${pnl:+,.2f} ({pnl_pct:+.1f}%)[/{color}]",
            )

        table.add_row("Total Invested", f"${summary.get('total_invested', 0):,.2f}")
        table.add_row("Last Action", summary.get("last_action") or "none")

        console.print(table)
    else:
        print(f"Status: mode={summary.get('mode')} | open={summary.get('open_count', 0)}")
        print(f"  Invested: ${summary.get('total_invested', 0):,.2f}")
        print(f"  Last: {summary.get('last_action', 'none')}")


def print_run_result(result: dict[str, Any]) -> None:
    """Print run result to terminal."""
    action = result.get("action", "UNKNOWN")
    success = result.get("success", False)
    dry_run = result.get("dry_run", False)
    mode = result.get("mode", "unknown")

    prefix = "[DRY RUN] " if dry_run else ""
    emoji = {"BUY": "✅", "SELL": "💰", "HOLD": "✋"}.get(action, "❓")

    if HAS_RICH and console:
        if result.get("fill"):
            fill = result["fill"]
            msg = (
                f"{prefix}{action} filled: {fill['filled_qty']:.5f} BTC "
                f"@ ${fill['avg_fill_price']:,.2f} | fee: ${fill['fee']:.2f}"
            )
        elif result.get("error"):
            msg = f"ERROR: {result['error']}"
        else:
            msg = f"{action} — {result.get('error', 'no action')}"

        color = "green" if success else "red"
        console.print(f"[{color}]{emoji} {msg}[/{color}]")
    else:
        print(f"{emoji} {prefix}{action} | mode={mode} | success={success}")
        if result.get("error"):
            print(f"  Error: {result['error']}")
