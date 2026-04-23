"""
MACD + Renko + Bollinger Bands Strategy — Console Mode Sample
=============================================================
Signal logic (MACDRenkoRangeSLByBB):
  - Entry: same as MACDRenko (Renko brick count + MACD direction)
  - Stop loss: placed at Bollinger Band mean or lower band (for longs),
               upper band or mean (for shorts)
  - Range filter: RangeTrendProcess suppresses signals during sideways markets
  - Optional take profit: set use_tp=True for TP = 2× the BB-derived stop distance

This combines three filters:
  1. Renko noise reduction
  2. MACD momentum confirmation
  3. Bollinger Band volatility-aware SL placement + range detection

It is the most complete of the built-in strategies and works well on
liquid FX pairs and index futures at 1h–4h timeframes.

Usage:
    python samples/bollinger_renko.py
"""

import datetime
import os
import sys

import dotenv

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from finance_client.csv.client import CSVClient
from finance_client.fprocess.fprocess.idcprocess import (
    MACDProcess,
    RenkoProcess,
    BBANDProcess,
    RangeTrendProcess,
)
import trade_strategy as ts

dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), "../tests/.env"))

# ── Configuration ─────────────────────────────────────────────────────────────

DATA_FOLDER = os.environ["ts_data_folder"]
SYMBOL_FILE = os.environ.get("ts_symbol_file", "yfinance_$symbol$_D1.csv")
FRAME_MINS = int(os.environ.get("ts_frame", 1440))

SYMBOL = "1333.T"
FILE_PATH = os.path.join(DATA_FOLDER, SYMBOL_FILE.replace("$symbol$", SYMBOL))

OHLC_COLUMNS = ["Open", "High", "Low", "Close"]
DATE_COLUMN = "Datetime"

RUN_MINUTES = 60

# ── Indicator processes ───────────────────────────────────────────────────────

# Start index must be > data_length + BB window to warm up all indicators
START_INDEX = 250
DATA_LENGTH = 120

macd_process = MACDProcess(
    short_window=12,
    long_window=26,
    signal_window=9,
    target_column=OHLC_COLUMNS[-1],
)

renko_process = RenkoProcess(
    window=60,              # ATR window for dynamic brick size
    ohlc_column=OHLC_COLUMNS,
)

# BB with alpha=2 gives ±2σ bands; used both for SL placement and range detection
bband_process = BBANDProcess(
    target_column=OHLC_COLUMNS[-1],
    alpha=2,
    window=20,
)

# Range/trend detector: returns range probability and trend slope
range_process = RangeTrendProcess(slope_window=3)

# ── Client & strategy ─────────────────────────────────────────────────────────

client = CSVClient(
    files=FILE_PATH,
    auto_step_index=True,
    frame=FRAME_MINS,
    start_index=START_INDEX,
    columns=OHLC_COLUMNS,
    date_column=DATE_COLUMN,
    slip_type="percent",
    do_render=False,
)

strategy = ts.strategies.MACDRenkoRangeSLByBB(
    finance_client=client,
    renko_process=renko_process,
    macd_process=macd_process,
    bolinger_process=bband_process,
    range_process=range_process,
    slope_window=5,         # slope window for MACD smoothing
    alpha=2,                # BB sigma multiplier (must match bband_process)
    threshold=2,            # minimum consecutive Renko bricks
    use_tp=False,           # set True to add TP = 2× BB stop distance
    interval_mins=-1,
    data_length=DATA_LENGTH,
    volume=1,
)

# ── Run with console ──────────────────────────────────────────────────────────

start_date = datetime.datetime.now()
end_date = start_date + datetime.timedelta(minutes=RUN_MINUTES)

manager = ts.StrategyManager(
    start_date=start_date,
    end_date=end_date,
    console_mode=True,
)

print(f"Starting MACD+Renko+BB on {SYMBOL} — /exit to stop.")
manager.start(strategy, wait=True)
