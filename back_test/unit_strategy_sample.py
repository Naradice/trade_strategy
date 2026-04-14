"""Backtest sample — declarative strategy via unit_strategy DSL.

Strategy logic (MACD cross + RSI filter, with a 2-bar consecutive confirmation):

  Entry (long):
    - MACD line has crossed above the Signal line (MACD - Signal > 0)
    - AND this cross has been sustained for 2 consecutive bars        ← ConsecutiveCount
    - AND RSI is below 70 (not overbought)

  Entry (short):
    - MACD line has crossed below the Signal line (MACD - Signal < 0)
    - AND sustained for 2 consecutive bars
    - AND RSI is above 30 (not oversold)

  Exit (direction-aware via exit_long_strategy / exit_short_strategy):
    - Long:  MACD crosses back below Signal, OR RSI >= 75
    - Short: MACD crosses back above Signal, OR RSI <= 25

Usage
-----
1. Copy `tests/.env.example` to `tests/.env` (or `back_test/.env`) and fill in:

     ts_data_folder=/path/to/csv/data
     ts_symbol_file=mt5_USDJPY_min$symbol$.csv   # or whichever pattern you use
     ts_frame=30

2. Run::

     cd trade_strategy
     python back_test/unit_strategy_sample.py
"""

import datetime
import json
import os
import sys

import dotenv

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(module_path)

finance_client_path = os.path.abspath(os.path.join(module_path, "../finance_client"))
sys.path.append(finance_client_path)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
from logging import config, getLogger

try:
    with open(os.path.join(module_path, "trade_strategy/settings.json"), "r") as f:
        settings = json.load(f)
except Exception as e:
    print(f"fail to load settings.json: {e}")
    raise

logger_config = settings["log"]
log_file_base_name = logger_config["handlers"]["fileHandler"]["filename"]
log_path = f'./{log_file_base_name}_unit_strategy_{datetime.datetime.now().strftime("%Y%m%d")}.log'
logger_config["handlers"]["fileHandler"]["filename"] = log_path
config.dictConfig(logger_config)
logger = getLogger("trade_strategy.back_test")

# ---------------------------------------------------------------------------
# Environment / data
# ---------------------------------------------------------------------------
dotenv.load_dotenv()
data_folder = os.environ["ts_data_folder"]
frame = int(os.environ.get("ts_frame", 30))

if frame == 1:
    file_path = os.path.abspath(f"{data_folder}/mt5_USDJPY_TickToMIN1.csv")
elif frame < 60:
    file_path = os.path.abspath(f"{data_folder}/mt5_USDJPY_min{frame}.csv")
else:
    file_path = os.path.abspath(f"{data_folder}/mt5_USDJPY_h{int(frame / 60)}.csv")

date_column = "time"
ohlc_columns = ["open", "high", "low", "close"]

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import trade_strategy as ts
from finance_client import db


def _make_storage(sqlite_path: str, provider: str, user: str):
    """Return a position storage object.  Uses PostgreSQL when PostgreServer env var is set, otherwise SQLite."""
    pg_host = os.environ.get("PostgreServer")
    if pg_host:
        return db.PositionPostgresStorage(
            provider=provider,
            username=user,
            host=pg_host,
            port=int(os.environ.get("PostgrePort", "5432")),
            database=os.environ.get("PostgreDatabase", "postgres"),
            user=os.environ.get("PostgreUsername", "postgres"),
            password=os.environ.get("PostgrePassword", ""),
        )
    if os.path.exists(sqlite_path):
        os.remove(sqlite_path)
    return db.PositionSQLiteStorage(sqlite_path, provider, user)
from finance_client.csv.client import CSVClient
from finance_client.fprocess.fprocess.idcprocess import MACDProcess, RSIProcess

from trade_strategy.unit_strategy import (
    BuyAction,
    CloseAction,
    ColumnIndicator,
    ConsecutiveCount,
    NoAction,
    SellAction,
    Strategy,
    UnitStrategyClient,
)


# ---------------------------------------------------------------------------
# Strategy builder
# ---------------------------------------------------------------------------

def build_strategy(macd_process: MACDProcess, rsi_process: RSIProcess):
    """Construct entry and exit strategy trees from the given indicator processes.

    The column names are read from the process objects so that custom keys
    (e.g. ``MACDProcess(key="my_macd")``) are handled automatically.
    """
    macd = ColumnIndicator(macd_process.KEY_MACD)
    signal_line = ColumnIndicator(macd_process.KEY_SIGNAL)
    rsi = ColumnIndicator(rsi_process.KEY_RSI)

    cross = macd - signal_line  # DerivedIndicator: positive when MACD > Signal

    # ---------- entry -------------------------------------------------------
    # Short: cross < 0 for 2 consecutive bars AND RSI > 30 → evaluated first
    # Long:  cross > 0 for 2 consecutive bars AND RSI < 70 → fallthrough
    long_entry = Strategy(
        condition=ConsecutiveCount(cross > 0) >= 2,
        true_operation=Strategy(
            condition=rsi < 70,
            true_operation=BuyAction(name="unit_macd_rsi"),
        ),
    )

    entry_strategy = Strategy(
        condition=ConsecutiveCount(cross < 0) >= 2,
        true_operation=Strategy(
            condition=rsi > 30,
            true_operation=SellAction(name="unit_macd_rsi"),
            false_operation=NoAction(),
        ),
        false_operation=long_entry,
    )

    # ---------- exit --------------------------------------------------------
    # Direction-aware: long and short positions have different reversal conditions.
    close_long = Strategy(
        condition=(cross < 0) | (rsi >= 75),
        true_operation=CloseAction(name="unit_macd_rsi"),
    )

    close_short = Strategy(
        condition=(cross > 0) | (rsi <= 25),
        true_operation=CloseAction(name="unit_macd_rsi"),
    )

    return entry_strategy, close_long, close_short


# ---------------------------------------------------------------------------
# Backtest runner
# ---------------------------------------------------------------------------

def run(user="unit_strategy_sample", provider="csv", minutes_to_run=10):
    db_path = "./unit_strategy_back_test.db"
    storage = _make_storage(db_path, provider, user)
    client = CSVClient(
        files=file_path,
        auto_step_index=True,
        frame=frame,
        start_index=100,
        columns=ohlc_columns,
        date_column=date_column,
        slip_type="percent",
        storage=storage,
    )

    macd_p = MACDProcess(short_window=12, long_window=26, signal_window=9, target_column=ohlc_columns[3])
    rsi_p = RSIProcess(key="rsi", window=14, column=ohlc_columns[3])

    entry_strategy, close_long, close_short = build_strategy(macd_p, rsi_p)

    strategy_client = UnitStrategyClient(
        finance_client=client,
        entry_strategy=entry_strategy,
        exit_long_strategy=close_long,
        exit_short_strategy=close_short,
        idc_processes=[macd_p, rsi_p],
        interval_mins=0,
        volume=1,
        data_length=100,
        logger=logger,
    )

    manager = ts.ParallelStrategyManager(
        [strategy_client],
        minutes=minutes_to_run,
        logger=logger,
        result_csv_path="./unit_strategy_result.csv",
    )
    manager.start_strategies()


# ---------------------------------------------------------------------------
# One-shot (step through all rows at once, no timer)
# ---------------------------------------------------------------------------

def run_onetime(user="unit_strategy_onetime", provider="csv"):
    """Run through the entire CSV in one shot using StrategyRunner.

    Useful for quick result inspection without waiting for a real-time timer.
    """
    db_path = "./unit_strategy_onetime.db"
    storage = _make_storage(db_path, provider, user)
    client = CSVClient(
        files=file_path,
        auto_step_index=True,
        frame=frame,
        start_index=100,
        columns=ohlc_columns,
        date_column=date_column,
        slip_type="percent",
        storage=storage,
    )

    macd_p = MACDProcess(short_window=12, long_window=26, signal_window=9, target_column=ohlc_columns[3])
    rsi_p = RSIProcess(key="rsi", window=14, ohlc_column_name=ohlc_columns)

    entry_strategy, close_long, close_short = build_strategy(macd_p, rsi_p)

    strategy_client = UnitStrategyClient(
        finance_client=client,
        entry_strategy=entry_strategy,
        exit_long_strategy=close_long,
        exit_short_strategy=close_short,
        idc_processes=[macd_p, rsi_p],
        interval_mins=0,
        volume=1,
        data_length=100,
        logger=logger,
    )

    symbols = client.symbols
    runner = ts.StrategyRunner(symbols)
    signals = runner.get_signals(strategy_client)
    logger.info(f"total signals generated: {len(signals)}")
    runner.handle_signals(strategy_client, signals)
    client.close_client()
    logger.info("one-shot backtest complete.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Switch between real-time simulation and one-shot mode:
    # run()           ← simulates real-time with ParallelStrategyManager
    run_onetime()   # ← steps through all CSV rows immediately
