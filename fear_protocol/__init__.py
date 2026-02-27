"""
fear-protocol: Exchange-agnostic sentiment-driven DCA framework.

Quick start:
    from fear_protocol import FearProtocol

    fp = FearProtocol()
    signal = fp.get_signal()
    print(signal)
"""
from fear_protocol.agent.api import FearProtocolAgent as FearProtocol
from fear_protocol.backtest.engine import BacktestEngine
from fear_protocol.core.models import (
    ActionType,
    BacktestConfig,
    BacktestResult,
    MarketContext,
    StrategySignal,
)

__version__ = "0.1.0"
__all__ = [
    "FearProtocol",
    "BacktestEngine",
    "ActionType",
    "BacktestConfig",
    "BacktestResult",
    "MarketContext",
    "StrategySignal",
]
