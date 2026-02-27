# Changelog

## [0.1.0] - 2026-02-27

### Added
- Core domain models (ActionType, MarketContext, StrategySignal, OrderResult, Position, BacktestResult)
- Financial math utilities (Sharpe, Sortino, drawdown, Kelly, Calmar)
- Exchange adapter interface with MockAdapter, PaperAdapter, HyperliquidAdapter
- FearGreedDCA strategy (ported from FearHarvester, backtested Sharpe 2.01)
- MomentumDCA strategy (consecutive red days + fear confirmation)
- GridFear strategy (grid DCA with increasing size at lower levels)
- Backtesting engine with streaming support
- Report generation (terminal, markdown, JSON)
- State manager with backwards-compatible FearHarvester format
- Agent integration API (FearProtocolAgent) with Pydantic schemas
- Typer CLI with signal, run, backtest, status commands
- Fear & Greed data provider (alternative.me API)
- Binance price provider with caching
- Historical data provider with local cache
- CI/CD with GitHub Actions
- 90%+ test coverage target
