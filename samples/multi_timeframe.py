"""
Multi-Timeframe Cascade Strategy — Console Mode Sample
======================================================
CascadeStrategyClient runs the same signal logic at several timeframes and
only opens a position when all frames agree on direction.  This dramatically
reduces false entries at the cost of fewer signals.

Setup here:
  - Base strategy: MACDRenko
  - Timeframes:    30 min → 1 h → 4 h (three-level confluence)
  - Close condition: "any" — close as soon as any frame gives a close signal

How it works:
  1. The 30-min frame generates candidate signals.
  2. The 1-h frame must agree (same buy/sell direction).
  3. The 4-h frame must agree.
  4. Only then is an order placed.

Usage:
    python samples/multi_timeframe.py

Note: the CSV file must contain enough bars to cover all three timeframes.
      At minimum you need ~2000 rows for 30-min data.
"""

import datetime
import os
import sys

import dotenv

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from finance_client.csv.client import CSVClient
from finance_client.fprocess.fprocess.idcprocess import MACDProcess, RenkoProcess
import trade_strategy as ts
from trade_strategy.strategies.strategy_client import CascadeStrategyClient

dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), "../tests/.env"))

# ── Configuration ─────────────────────────────────────────────────────────────

DATA_FOLDER = os.environ["ts_data_folder"]
SYMBOL_FILE = os.environ.get("ts_symbol_file", "yfinance_$symbol$_D1.csv")
# Multi-timeframe works best with sub-daily data; adjust to your dataset.
FRAME_MINS = int(os.environ.get("ts_frame", 30))

SYMBOL = "1333.T"
FILE_PATH = os.path.join(DATA_FOLDER, SYMBOL_FILE.replace("$symbol$", SYMBOL))

OHLC_COLUMNS = ["Open", "High", "Low", "Close"]
DATE_COLUMN = "Datetime"

# Three timeframes (minutes).  The cascade client resamples internally.
CASCADE_FRAMES = [30, 60, 240]   # 30 min, 1 h, 4 h

RUN_MINUTES = 60

# ── Build the base MACDRenko strategy ────────────────────────────────────────
# The same strategy instance is evaluated at each cascade frame.

client = CSVClient(
    files=FILE_PATH,
    auto_step_index=True,
    frame=FRAME_MINS,
    start_index=2000,        # needs a long warm-up for 4-h resampling
    columns=OHLC_COLUMNS,
    date_column=DATE_COLUMN,
    slip_type="percent",
    do_render=False,
)

macd_process = MACDProcess(
    short_window=12,
    long_window=26,
    signal_window=9,
    target_column=OHLC_COLUMNS[-1],
)

renko_process = RenkoProcess(
    window=14,
    ohlc_column=OHLC_COLUMNS,
)

base_strategy = ts.strategies.MACDRenko(
    finance_client=client,
    renko_process=renko_process,
    macd_process=macd_process,
    slope_window=2,
    threshold=1,
    interval_mins=0,        # 0 = run immediately each time it is called
    data_length=500,
    volume=1,
)

# ── Wrap in CascadeStrategyClient ────────────────────────────────────────────

cascade_strategy = CascadeStrategyClient(
    strategies=base_strategy,           # single strategy evaluated at each frame
    cascade_frames=CASCADE_FRAMES,
    finance_client=client,
    close_condition="any",              # close as soon as any frame says close
    interval_mins=CASCADE_FRAMES[0],    # wake up every 30 min
    volume=1,
    data_length=500,
)

# ── Run with console ──────────────────────────────────────────────────────────

start_date = datetime.datetime.now()
end_date = start_date + datetime.timedelta(minutes=RUN_MINUTES)

manager = ts.StrategyManager(
    start_date=start_date,
    end_date=end_date,
    console_mode=True,
)

print(
    f"Starting Multi-Timeframe MACD+Renko on {SYMBOL} "
    f"({'/'.join(str(f) for f in CASCADE_FRAMES)} min) — /exit to stop."
)
manager.start(cascade_strategy, wait=True)
