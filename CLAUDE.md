# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Run from the `trade_strategy/` directory:

```bash
# Install in development mode
python setup.py develop

# Run all tests
python -m pytest tests/

# Run a single test file
python -m unittest tests/basic_test.py

# Run a specific test
python -m unittest tests.basic_test.Test.test_strategy_base
```

**Formatting:** Black with `line-length = 150`, target Python 3.12+.

### Test environment

Tests require a `.env` file in `tests/` (see `tests/sample.env`):
```
ts_data_folder=C:\your_folder
ts_symbol_file=yfinance_$symbol$_D1.csv
ts_frame=1440
GOOGLE_API_KEY=your_api_key   # only needed for agent/pipeline tests
```

The `LLM_MODEL` env var controls which LLM the agent pipeline uses (defaults to `gemini-2.0-flash`).

## Architecture

### Two-layer signal design

**Layer 1 — pure functions** (`strategies/strategy.py`): Stateless signal-detection logic (e.g. `macd_renko`, `cci_cross`, `slope_change`). Each function takes a DataFrame + current position and returns a `Signal` subclass or `None`. No state, no side effects — easy to unit-test and reuse.

**Layer 2 — `StrategyClient` subclasses** (`strategies/strategy_client.py`, `strategies/strategy_base.py`): Wrap a `finance_client.ClientBase`, register indicator processes via `add_indicaters()`, and expose `get_signal(df, position, symbol) → Signal`. The base `StrategyClient.run()` method fetches OHLC data with indicators applied, iterates over symbols/positions, and calls `get_signal()`.

New strategies should follow this split: pure logic in `strategy.py`, stateful wrapper in `strategy_client.py`.

### Signal types (`signal.py`)

Signals carry: `is_buy` (True/False/None), `is_close`, `order_type`, `order_price`, `tp`, `sl`, `volume`, `symbol`. Key subtypes:
- `BuySignal` / `SellSignal` — open a market position
- `BuyPendingOrderSignal` / `SellPendingOrderSignal` — pending/limit orders
- `CloseBuySignal` / `CloseSellSignal` — close the opposite-side position and optionally open new
- `CloseSignal` — close all positions for the symbol
- `id=10` is the sentinel for "close only, don't open"

### Execution layer (`main.py`)

- `StrategyRunner` — single-threaded helper used by both live trading and backtesting. Calls `strategy.run()` for signals, then dispatches `client.open_trade()` / `client.close_*_positions()`.
- `ParallelStrategyManager` — runs multiple `StrategyClient` instances in threads, aligns wake-up to candle boundaries (`_sleep_until_frame_time`), logs win-rate statistics on exit, and optionally writes a result CSV.

### Backtesting (`backtest.py`)

`BacktestRunner` wraps `StrategyRunner` for offline replay over a `CSVClient`. It steps through bars until `StopIteration` (data exhausted) and returns `{symbol: [profits]}`.

```python
runner = BacktestRunner(strategy, symbols="EURUSD")
results = runner.run(on_step=lambda n: print(f"Step {n}"))
```

### AI Pipeline (`pipeline.py`, `agents/`)

`TradingPipeline` is an optional decorator around the signal loop. It uses Google ADK agents:
- `before_signal()` — runs a `trend_analyst_agent` to update `strategy.market_trends[symbol]` before each signal cycle.
- `after_signal()` — runs a `signal_refiner_agent` (sequential: signal analyst → price refiner) to filter or adjust the signals from the strategy.

Agents are defined in `agents/agent.py` using `google.adk`. The `LLM_MODEL` env var selects the model.

### `CascadeStrategyClient`

Runs multiple strategies at different timeframes and requires agreement across all of them before returning a signal. `close_condition` (`"any"`, `"all"`, `"first"`, `"last"`) controls which strategy's close signal wins.

### `UnitStrategyClient` (`unit_strategy/client.py`)

An alternative composition model: strategies are expressed as lists of callable `open_units` and `close_units` that return a score in `[-1, 1]`. A threshold gates actual order submission. This is experimental and separate from the `StrategyClient` hierarchy.

## Key dependency

`finance_client` (sibling package at `../finance_client`) provides `ClientBase`, `fprocess` indicators, and `Position`. The `CSVClient` is used for backtesting; live clients (MT5, Oanda, etc.) are drop-in replacements.
