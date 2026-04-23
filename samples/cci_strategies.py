"""
CCI Strategies — Console Mode Sample
=====================================
Two strategies demonstrated side by side on different symbols:

  1. CCICross  — trades the CCI zero-line crossover
       BUY  when CCI crosses above 0 (positive momentum)
       SELL when CCI crosses below 0

  2. CCIBoader — trades CCI extremes (overbought / oversold)
       BUY  when CCI breaks above +100 (strong momentum continuation)
       SELL when CCI breaks below -100
       Closes when CCI returns inside the band

Running both simultaneously shows ParallelStrategyManager with console mode.

Usage:
    python samples/cci_strategies.py
"""

import datetime
import os
import sys

import dotenv

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from finance_client.csv.client import CSVClient
from finance_client.fprocess.fprocess.idcprocess import CCIProcess
import trade_strategy as ts

dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), "../tests/.env"))

# ── Configuration ─────────────────────────────────────────────────────────────

DATA_FOLDER = os.environ["ts_data_folder"]
SYMBOL_FILE = os.environ.get("ts_symbol_file", "yfinance_$symbol$_D1.csv")
FRAME_MINS = int(os.environ.get("ts_frame", 1440))

OHLC_COLUMNS = ["Open", "High", "Low", "Close"]
DATE_COLUMN = "Datetime"

SYMBOL_A = "1333.T"
SYMBOL_B = "1332.T"

RUN_MINUTES = 60

def make_client(symbol: str, start_index: int = 100) -> CSVClient:
    file_path = os.path.join(DATA_FOLDER, SYMBOL_FILE.replace("$symbol$", symbol))
    return CSVClient(
        files=file_path,
        auto_step_index=True,
        frame=FRAME_MINS,
        start_index=start_index,
        columns=OHLC_COLUMNS,
        date_column=DATE_COLUMN,
        slip_type="percent",
        do_render=False,
    )

# ── Strategy 1: CCI Cross (zero-line) ────────────────────────────────────────

client_a = make_client(SYMBOL_A)

cci_process_a = CCIProcess(window=20)  # classic 20-period CCI

cci_cross = ts.strategies.CCICross(
    finance_client=client_a,
    cci_process=cci_process_a,
    interval_mins=-1,
    data_length=100,
    volume=1,
)

# ── Strategy 2: CCI Border (±100 overbought/oversold) ────────────────────────

client_b = make_client(SYMBOL_B)

cci_process_b = CCIProcess(window=20)

cci_border = ts.strategies.CCIBoader(
    finance_client=client_b,
    cci_process=cci_process_b,
    upper=100,    # buy above this level (momentum continuation)
    lower=-100,   # sell below this level
    interval_mins=-1,
    data_length=100,
    volume=1,
)

# ── Run both strategies in parallel with console ──────────────────────────────
# ParallelStrategyManager requires at least 2 strategies.

start_date = datetime.datetime.now()
end_date = start_date + datetime.timedelta(minutes=RUN_MINUTES)

manager = ts.main.ParallelStrategyManager(
    start_date=start_date,
    end_date=end_date,
    console_mode=True,
)

print(f"Starting CCI strategies on {SYMBOL_A} (cross) and {SYMBOL_B} (border) — /exit to stop.")
manager.start([cci_cross, cci_border], wait=True)
