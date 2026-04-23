"""
MACD Cross Strategy — Console Mode Sample
==========================================
Signal logic:
  - BUY  when MACD line crosses above the Signal line
  - SELL when MACD line crosses below the Signal line

This is the simplest trend-following approach: trade every crossover of the
standard MACD histogram (12/26/9).  Works best on trending instruments and
longer timeframes (1h / daily).

Usage:
    Set the env vars in .env (see tests/sample.env), then run:
        python samples/macd_cross.py

Console commands (while running):
    /disable        — stop opening new positions (both sides)
    /disable long   — stop opening long positions
    /disable short  — stop opening short positions
    /enable         — re-enable all positions
    /exit           — stop the strategy
"""

import datetime
import os
import sys

import dotenv

# Allow running from the project root without installing
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from finance_client.csv.client import CSVClient
from finance_client.fprocess.fprocess.idcprocess import MACDProcess
import trade_strategy as ts

dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), "../tests/.env"))

# ── Configuration ─────────────────────────────────────────────────────────────

DATA_FOLDER = os.environ["ts_data_folder"]
SYMBOL_FILE = os.environ.get("ts_symbol_file", "yfinance_$symbol$_D1.csv")
FRAME_MINS = int(os.environ.get("ts_frame", 1440))  # 1440 = daily

SYMBOL = "1333.T"
FILE_PATH = os.path.join(DATA_FOLDER, SYMBOL_FILE.replace("$symbol$", SYMBOL))

OHLC_COLUMNS = ["Open", "High", "Low", "Close"]
DATE_COLUMN = "Datetime"

# MACD parameters (classic 12/26/9)
MACD_SHORT = 12
MACD_LONG = 26
MACD_SIGNAL = 9

# How long to run (set a short window for demonstration)
RUN_MINUTES = 60

# ── Strategy setup ────────────────────────────────────────────────────────────

client = CSVClient(
    files=FILE_PATH,
    auto_step_index=True,   # advance one bar per strategy cycle (backtest mode)
    frame=FRAME_MINS,
    start_index=100,        # skip the first 100 bars so MACD has enough history
    columns=OHLC_COLUMNS,
    date_column=DATE_COLUMN,
    slip_type="percent",    # simulate realistic fill slippage
    do_render=False,
)

macd_process = MACDProcess(
    short_window=MACD_SHORT,
    long_window=MACD_LONG,
    signal_window=MACD_SIGNAL,
    target_column=OHLC_COLUMNS[-1],  # "Close"
)

strategy = ts.strategies.MACDCross(
    finance_client=client,
    macd_process=macd_process,
    interval_mins=-1,   # -1 = use client frame (runs every bar)
    data_length=100,
    volume=1,
)

# ── Run with console ──────────────────────────────────────────────────────────

start_date = datetime.datetime.now()
end_date = start_date + datetime.timedelta(minutes=RUN_MINUTES)

manager = ts.StrategyManager(
    start_date=start_date,
    end_date=end_date,
    console_mode=True,   # interactive curses terminal UI
)

print(f"Starting MACD Cross on {SYMBOL} — press Ctrl+C or type /exit to stop.")
manager.start(strategy, wait=True)
