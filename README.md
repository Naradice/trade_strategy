# trade_strategy

Strategy execution framework for algorithmic trading, built on top of `finance_client`. Provides signal generation, backtesting, live execution, and an optional AI-powered pipeline using Google ADK agents.

Part of a monorepo — see the parent `finance_client/` package for broker clients, risk management, and indicators.

## Installation

```bash
# From trade_strategy/ directory
python setup.py develop
```

Requires `finance_client` from the sibling directory to be installed first.

## Quick Start

### Live trading

```python
from trade_strategy.main import StrategyManager
from trade_strategy.strategies.strategy_client import MACDRenko  # example strategy
import datetime

client = ...  # any finance_client.ClientBase implementation
strategy = MACDRenko(client, interval_mins=60)

manager = StrategyManager(
    start_date=datetime.datetime.now(),
    end_date=datetime.datetime(2026, 12, 31),
)
manager.start(strategy)
```

### Backtesting

```python
from trade_strategy.backtest import BacktestRunner
from finance_client.csv.client import CSVClient

csv_client = CSVClient(...)
strategy = MyStrategy(csv_client)

runner = BacktestRunner(strategy, symbols="EURUSD")
results = runner.run(on_step=lambda n: print(f"Step {n}"))
# results: {"EURUSD": [profit1, profit2, ...]}
```

### Multiple strategies in parallel

```python
from trade_strategy.main import ParallelStrategyManager

manager = ParallelStrategyManager(start_date=..., end_date=...)
manager.start([strategy_a, strategy_b, strategy_c])
```

## Architecture

### Two-layer signal design

**Layer 1 — pure functions** ([strategies/strategy.py](trade_strategy/strategies/strategy.py))
Stateless signal-detection logic (e.g. `macd_renko`, `cci_cross`, `slope_change`). Each function takes a DataFrame + current position and returns a `Signal` subclass or `None`. No state, no side effects — easy to unit-test and reuse.

**Layer 2 — `StrategyClient` subclasses** ([strategies/strategy_base.py](trade_strategy/strategies/strategy_base.py), [strategies/strategy_client.py](trade_strategy/strategies/strategy_client.py))
Wrap a `finance_client.ClientBase`, register indicator processes via `add_indicaters()`, and expose `get_signal(df, position, symbol) → Signal`.

New strategies should follow this split: pure logic in `strategy.py`, stateful wrapper in `strategy_client.py`.

### Signal types ([signal.py](trade_strategy/signal.py))

| Class | `id` | Description |
|---|---|---|
| `BuySignal` | 1 | Open long market order |
| `SellSignal` | -1 | Open short market order |
| `BuyPendingOrderSignal` | 2 | Open long limit/stop order |
| `SellPendingOrderSignal` | -2 | Open short limit/stop order |
| `CloseSignal` | 10 | Close all positions for symbol |
| `CloseBuySignal` | 11 | Close short positions, optionally open long |
| `CloseSellSignal` | -11 | Close long positions, optionally open short |

All signals carry: `symbol`, `order_price`, `tp`, `sl`, `volume`, `confidence`, `is_buy`, `is_close`.

`id=10` is a sentinel meaning "close only, do not open a new position".

### Execution layer ([main.py](trade_strategy/main.py))

- `StrategyRunner` — single-threaded helper. Calls `strategy.run()` for signals, dispatches `client.open_trade()` / `client.close_*_positions()`. Used by both live trading and backtesting.
- `StrategyManager` — single-strategy live runner with timer, console, and signal handling.
- `ParallelStrategyManager` — runs multiple `StrategyClient` instances in threads, each on its own candle interval. Logs win-rate statistics on exit.

### Backtesting ([backtest.py](trade_strategy/backtest.py))

`BacktestRunner` wraps `StrategyRunner` for offline replay over a `CSVClient`. Steps through bars until `StopIteration` (data exhausted) and returns `{symbol: [profits]}`.

### AI Pipeline ([pipeline.py](trade_strategy/pipeline.py), [agents/](trade_strategy/agents/))

Optional decorator around the signal loop using Google ADK agents:

- `before_signal()` — runs a `trend_analyst_agent` to update `strategy.market_trends[symbol]` before each signal cycle.
- `after_signal()` — runs a `signal_refiner_agent` (sequential: signal analyst → price refiner) to filter or adjust signals.

```python
from trade_strategy.pipeline import TradingPipeline

pipeline = TradingPipeline(ohlc_tool=my_tool)
runner = StrategyRunner(symbols, pipeline=pipeline)
```

Set `LLM_MODEL` env var to choose the model (defaults to `gemini-2.0-flash`).

### `CascadeStrategyClient`

Runs multiple strategies at different timeframes and requires agreement across all of them before returning a signal. `close_condition` (`"any"`, `"all"`, `"first"`, `"last"`) controls which strategy's close signal wins.

### `UnitStrategyClient` ([unit_strategy/](trade_strategy/unit_strategy/))

Experimental composition model: strategies are expressed as lists of callable `open_units` / `close_units` returning a score in `[-1, 1]`. A threshold gates order submission. Separate from the `StrategyClient` hierarchy.

## Samples

Ready-to-run scripts in [samples/](samples/) demonstrate each built-in strategy with console mode. All scripts read CSV data via `CSVClient` and use `StrategyManager(console_mode=True)` so you can type commands while they run.

| File | Strategy | Key indicators |
|---|---|---|
| [macd_cross.py](samples/macd_cross.py) | MACD Cross | MACD 12/26/9 zero-line crossover |
| [macd_renko.py](samples/macd_renko.py) | MACD + Renko | Renko brick count + MACD direction, ATR trailing stop, range filter |
| [cci_strategies.py](samples/cci_strategies.py) | CCI Cross & CCI Border | CCI zero-line / ±100 overbought-oversold (two symbols in parallel) |
| [bollinger_renko.py](samples/bollinger_renko.py) | MACD + Renko + Bollinger Bands | Renko + MACD + BB stop-loss placement + range detection |
| [multi_timeframe.py](samples/multi_timeframe.py) | Multi-Timeframe Cascade | MACD+Renko confirmed across 30 min / 1 h / 4 h |

**Setup** — copy `tests/sample.env` to `tests/.env` and fill in `ts_data_folder` and related vars, then:

```bash
python samples/macd_cross.py
```

**Console commands** (available while any sample is running):

| Command | Effect |
|---|---|
| `/disable` | Stop opening new positions (both sides) |
| `/disable long` | Stop opening long positions |
| `/disable short` | Stop opening short positions |
| `/enable` | Re-enable all positions |
| `/exit` | Stop the strategy |

## Tests

Tests require a `.env` file in `tests/` (copy from `tests/sample.env`):

```
ts_data_folder=C:\your_folder
ts_symbol_file=yfinance_$symbol$_D1.csv
ts_frame=1440
GOOGLE_API_KEY=your_api_key   # only needed for agent/pipeline tests
```

```bash
# Run all tests
python -m pytest tests/

# Run a single test file
python -m unittest tests/basic_test.py

# Run a specific test
python -m unittest tests.basic_test.Test.test_strategy_base
```

## Dependencies

- `finance_client` — sibling package providing `ClientBase`, `fprocess` indicators, `Position`, and `CSVClient`
- `windows-curses` — console support on Windows
- `google-adk` — optional, required only for `TradingPipeline`
