"""Backtest report generation — terminal, markdown, JSON output."""
from __future__ import annotations

import json
from pathlib import Path

from fear_protocol.core.models import BacktestResult


class BacktestReport:
    """
    Generate backtest reports in various formats.

    Formats: terminal (Rich), markdown, JSON.
    """

    def __init__(self, result: BacktestResult) -> None:
        """
        Initialize the report.

        Args:
            result: Complete backtest result.
        """
        self.result = result

    def to_dict(self) -> dict:
        """Return full result as JSON-serializable dict."""
        return self.result.to_dict()

    def to_json(self, path: Path) -> None:
        """
        Write JSON report to file.

        Args:
            path: Output file path.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))

    def to_markdown(self) -> str:
        """Return human-readable markdown summary."""
        r = self.result
        d = r.to_dict()
        lines = [
            f"# Backtest Results: {d['strategy']}",
            f"",
            f"**Period:** {d['start_date']} → {d['end_date']}",
            f"",
            f"## Performance Metrics",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Return | {d['total_return_pct']:+.1f}% |",
            f"| Annualized Return | {d['annualized_return_pct']:+.1f}% |",
            f"| Sharpe Ratio | {d['sharpe_ratio']:.2f} |",
            f"| Sortino Ratio | {d['sortino_ratio']:.2f} |",
            f"| Max Drawdown | {d['max_drawdown_pct']:.1f}% |",
            f"| Calmar Ratio | {d['calmar_ratio']:.2f} |",
            f"| Win Rate | {d['win_rate_pct']:.1f}% |",
            f"| Avg Win | {d['avg_win_pct']:+.1f}% |",
            f"| Avg Loss | {d['avg_loss_pct']:+.1f}% |",
            f"| Profit Factor | {d['profit_factor']:.2f} |",
            f"| Total Trades | {d['total_trades']} |",
            f"| Avg Hold Days | {d['avg_hold_days']:.1f} |",
            f"",
            f"## vs BTC Buy-and-Hold",
            f"",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| BTC Hold Return | {d['btc_hold_return_pct']:+.1f}% |",
            f"| Alpha | {d['alpha']:+.1f}% |",
        ]
        verdict = "✅ DEPLOY" if d["sharpe_ratio"] >= 1.5 else "⚠️ NEEDS WORK"
        lines.append(f"\n**Verdict:** Sharpe {d['sharpe_ratio']:.2f} → {verdict}")
        return "\n".join(lines)

    def to_html(self) -> str:
        """Return a minimal HTML report string."""
        d = self.result.to_dict()
        rows = "".join(
            f"<tr><td>{k}</td><td>{v}</td></tr>"
            for k, v in d.items()
            if k != "trades"
        )
        return (
            f"<html><head><title>fear-protocol backtest</title></head>"
            f"<body><h1>fear-protocol Backtest: {d['strategy']}</h1>"
            f"<p>{d['start_date']} → {d['end_date']}</p>"
            f"<table>{rows}</table>"
            f"<p>Total Return: {d['total_return_pct']:+.1f}%</p>"
            f"</body></html>"
        )

    def print_summary(self) -> None:
        """Print Rich terminal table output."""
        try:
            from rich.console import Console
            from rich.table import Table
            from rich import box

            r = self.result
            d = r.to_dict()
            console = Console()

            table = Table(
                title=f"Backtest: {d['strategy']} ({d['start_date']} → {d['end_date']})",
                box=box.ROUNDED,
                show_header=True,
            )
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="bold")

            sharpe_color = "green" if d["sharpe_ratio"] >= 1.5 else "yellow"
            dd_color = "red" if d["max_drawdown_pct"] < -30 else "yellow"

            table.add_row("Total Return", f"{d['total_return_pct']:+.1f}%")
            table.add_row("Annualized Return", f"{d['annualized_return_pct']:+.1f}%")
            table.add_row(
                "Sharpe Ratio",
                f"[{sharpe_color}]{d['sharpe_ratio']:.2f}[/{sharpe_color}]",
            )
            table.add_row("Sortino Ratio", f"{d['sortino_ratio']:.2f}")
            table.add_row(
                "Max Drawdown",
                f"[{dd_color}]{d['max_drawdown_pct']:.1f}%[/{dd_color}]",
            )
            table.add_row("Calmar Ratio", f"{d['calmar_ratio']:.2f}")
            table.add_row("Win Rate", f"{d['win_rate_pct']:.1f}%")
            table.add_row("Profit Factor", f"{d['profit_factor']:.2f}")
            table.add_row("Total Trades", str(d["total_trades"]))
            table.add_row("Avg Hold Days", f"{d['avg_hold_days']:.1f}d")
            table.add_row("BTC Hold Return", f"{d['btc_hold_return_pct']:+.1f}%")
            table.add_row("Alpha", f"{d['alpha']:+.1f}%")

            console.print(table)

            verdict = "✅ DEPLOY" if d["sharpe_ratio"] >= 1.5 else "⚠️ NEEDS WORK"
            console.print(f"\nVerdict: Sharpe {d['sharpe_ratio']:.2f} → {verdict}\n")

        except ImportError:
            # Fallback without Rich
            d = self.result.to_dict()
            print(f"\n{'='*50}")
            print(f"Backtest: {d['strategy']} ({d['start_date']} → {d['end_date']})")
            print(f"{'='*50}")
            for k, v in d.items():
                if k != "trades":
                    print(f"  {k}: {v}")
