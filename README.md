# fear-protocol

**Exchange-agnostic sentiment-driven DCA framework.**

Born from FearHarvester (backtested Sharpe 2.01), fear-protocol extracts the core insight — *extreme fear is the best buying signal in crypto* — into a composable, testable, agent-native platform.

## Quickstart

```bash
# Install
uv add fear-protocol

# Check current Fear & Greed signal
fear-protocol signal

# Dry-run the strategy
fear-protocol run --mode dry-run

# Backtest 2020-2024
fear-protocol backtest --start 2020-01-01

# Paper trade
fear-protocol run --exchange paper --mode paper
```

## Core Insight

Buying BTC when F&G ≤ 20 and holding 120 days: **Sharpe 2.01**.

## Architecture

```
fear_protocol/
├── core/           ← pure domain logic (models, math)
├── data/           ← data providers (fear/greed, prices, historical)
├── strategies/     ← pluggable strategies
├── exchanges/      ← exchange adapters (HL, Binance, Mock, Paper)
├── backtest/       ← backtesting engine
├── state/          ← position & portfolio state
├── agent/          ← agent integration (async API, JSON-RPC)
└── cli/            ← Typer CLI
```

## Strategies

| Strategy | Description | Sharpe |
|----------|-------------|--------|
| `fear-greed-dca` | DCA on extreme fear (F&G ≤ 20), hold 120d | 2.01 |
| `momentum-dca` | DCA after N consecutive red days + fear | TBD |
| `grid-fear` | Grid DCA at stepped levels during fear | TBD |

## Exchanges

| Adapter | Type | Notes |
|---------|------|-------|
| `mock` | Deterministic | For backtesting & tests |
| `paper` | Paper trading | Real prices, simulated fills |
| `hyperliquid` | Live | UBTC/USDC spot |
| `binance` | Live | BTC/USDT spot |

## Agent Integration

```python
from fear_protocol import FearProtocol

fp = FearProtocol()
signal = fp.get_signal()
# → {"action": "BUY", "confidence": 0.87, "fear_greed": 12, ...}
```

## License

MIT
