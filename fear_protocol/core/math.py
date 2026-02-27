"""Financial math utilities: Sharpe, Sortino, drawdown, Kelly sizing."""
from __future__ import annotations

import math
import statistics
from decimal import Decimal


def sharpe_ratio(returns: list[float], risk_free_rate: float = 0.0) -> float:
    """
    Calculate Sharpe ratio from a list of period returns.

    Args:
        returns: List of period returns (e.g., per-trade % returns).
        risk_free_rate: Risk-free rate for the same period (default 0).

    Returns:
        Sharpe ratio, or 0.0 if insufficient data.
    """
    if len(returns) < 2:
        return 0.0
    excess = [r - risk_free_rate for r in returns]
    mean_excess = statistics.mean(excess)
    std_excess = statistics.stdev(excess)
    if std_excess == 0:
        return 0.0
    return mean_excess / std_excess


def sortino_ratio(returns: list[float], risk_free_rate: float = 0.0) -> float:
    """
    Calculate Sortino ratio (uses downside deviation instead of total std).

    Args:
        returns: List of period returns.
        risk_free_rate: Minimum acceptable return (default 0).

    Returns:
        Sortino ratio, or 0.0 if insufficient data.
    """
    if len(returns) < 2:
        return 0.0
    excess = [r - risk_free_rate for r in returns]
    mean_excess = statistics.mean(excess)
    downside = [r for r in excess if r < 0]
    if not downside:
        return float("inf") if mean_excess > 0 else 0.0
    downside_dev = math.sqrt(statistics.mean([r**2 for r in downside]))
    if downside_dev == 0:
        return 0.0
    return mean_excess / downside_dev


def max_drawdown(equity_curve: list[float]) -> float:
    """
    Calculate maximum drawdown from an equity curve.

    Args:
        equity_curve: List of portfolio values over time.

    Returns:
        Maximum drawdown as a negative percentage (e.g., -25.3).
    """
    if len(equity_curve) < 2:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for value in equity_curve:
        if value > peak:
            peak = value
        drawdown = (value - peak) / peak * 100
        if drawdown < max_dd:
            max_dd = drawdown
    return max_dd


def calmar_ratio(annualized_return: float, max_dd: float) -> float:
    """
    Calculate Calmar ratio (annualized return / absolute max drawdown).

    Args:
        annualized_return: Annualized return percentage.
        max_dd: Maximum drawdown percentage (negative number).

    Returns:
        Calmar ratio, or 0.0 if max_dd is zero.
    """
    abs_dd = abs(max_dd)
    if abs_dd == 0:
        return 0.0
    return annualized_return / abs_dd


def annualized_return(total_return_pct: float, days: int) -> float:
    """
    Convert a total return over N days to an annualized return.

    Args:
        total_return_pct: Total return as percentage (e.g., 150.0 for 150%).
        days: Number of days the strategy was running.

    Returns:
        Annualized return as percentage.
    """
    if days <= 0:
        return 0.0
    total_factor = 1 + total_return_pct / 100
    if total_factor <= 0:
        return -100.0
    years = days / 365.0
    ann_factor = total_factor ** (1 / years) - 1
    return ann_factor * 100


def kelly_fraction(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """
    Calculate Kelly fraction for position sizing.

    Args:
        win_rate: Win probability (0.0–1.0).
        avg_win: Average winning trade return (positive, e.g., 0.25 for 25%).
        avg_loss: Average losing trade return (positive magnitude, e.g., 0.10 for 10%).

    Returns:
        Kelly fraction (0.0–1.0). Clamped to [0, 1].
    """
    if avg_loss == 0:
        return 0.0
    odds = avg_win / avg_loss
    k = win_rate - (1 - win_rate) / odds
    return max(0.0, min(1.0, k))


def profit_factor(wins: list[float], losses: list[float]) -> float:
    """
    Calculate profit factor (gross profit / gross loss).

    Args:
        wins: List of winning trade returns (positive values).
        losses: List of losing trade returns (can be negative or positive magnitudes).

    Returns:
        Profit factor, or 0.0 if no losses.
    """
    gross_profit = sum(w for w in wins if w > 0)
    gross_loss = sum(abs(l) for l in losses if l < 0)
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def position_size_usd(
    capital: Decimal,
    kelly_frac: float,
    max_amount: Decimal,
) -> Decimal:
    """
    Calculate position size in USD using Kelly fraction.

    Args:
        capital: Available capital in USD.
        kelly_frac: Kelly fraction (0.0–1.0).
        max_amount: Maximum allowed position size.

    Returns:
        Position size in USD, capped at max_amount.
    """
    kelly_amount = capital * Decimal(str(kelly_frac))
    return min(kelly_amount, max_amount)
