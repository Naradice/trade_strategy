"""
MACD + Renko Strategy — Console Mode Sample
============================================
Signal logic:
  - BUY  when Renko has N+ consecutive up-bricks AND MACD is above Signal
  - SELL when Renko has N+ consecutive down-bricks AND MACD is below Signal

Renko charts filter out small price moves.  Combining Renko brick count with
MACD direction reduces whipsaws significantly compared to pure MACD Cross.

Optional extras demonstrated here:
  - ATR-based stop loss (risk_option)
  - ATR trailing stop (trailing_stop)
  - Bollinger Band range filter (range_function): skip signals during congestion

Usage:
    python samples/macd_renko.py
"""

import datetime
import os
import sys

import dotenv

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from finance_client.csv.client import CSVClient
from finance_client.config import AccountRiskConfig
from finance_client.fprocess.fprocess.idcprocess import MACDProcess, RenkoProcess
from finance_client.fprocess import fprocess
from finance_client.risk_manager.risk_options import ATRRisk
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

# ── Optional risk management ──────────────────────────────────────────────────

# Account-level caps (set to None to disable)
account_risk_config = AccountRiskConfig(
    base_currency="JPY",
    max_single_trade_percent=None,
    max_total_risk_percent=None,
    daily_max_loss_percent=None,
    allow_aggressive_mode=False,
    aggressive_multiplier=None,
    enforce_volume_reduction=True,
    atr_ratio_min_stop_loss=None,
)

# Per-trade stop loss sized to ATR (1% equity risk, 2:1 R/R)
risk_option = ATRRisk(
    percent=1.0,
    atr_window=14,
    atr_multiplier=6.0,
    ohlc_columns=OHLC_COLUMNS,
    rr_ratio=2.0,
)

# ATR trailing stop — moves stop up/down as price moves in your favour
trailing_stop = ts.trailingstop.TrailingStopByATR(
    atr_window=7,
    atr_multiplier=3.0,
    ohlc_columns=OHLC_COLUMNS,
    clip_with_price=False,
)

# Range filter: skip signals when Bollinger Bands are wide (volatile / trending)
# Returns True (= "in range") when the ratio of BB width to std is below a threshold.
range_function = lambda df: fprocess.regime.range_detection_by_bollinger(
    df,
    std_window=200,
    window=20,
    std_threshold=0.6,
    ohlc_columns=OHLC_COLUMNS,
)

# ── Strategy setup ────────────────────────────────────────────────────────────

client = CSVClient(
    files=FILE_PATH,
    auto_step_index=True,
    frame=FRAME_MINS,
    start_index=100,
    columns=OHLC_COLUMNS,
    date_column=DATE_COLUMN,
    slip_type="percent",
    do_render=False,
    account_risk_config=account_risk_config,
    risk_option=risk_option,
)

macd_process = MACDProcess(
    short_window=12,
    long_window=26,
    signal_window=9,
    target_column=OHLC_COLUMNS[-1],
)

# Renko brick size auto-derived from ATR(window) of the OHLC data
renko_process = RenkoProcess(
    window=14,
    ohlc_column=OHLC_COLUMNS,
)

strategy = ts.strategies.MACDRenko(
    finance_client=client,
    renko_process=renko_process,
    macd_process=macd_process,
    slope_window=5,     # smooth MACD with a slope indicator
    threshold=2,        # require 2+ consecutive bricks before signalling
    interval_mins=-1,
    data_length=150,
    volume=1,
    trailing_stop=trailing_stop,
    range_function=range_function,
)

# ── Run with console ──────────────────────────────────────────────────────────

start_date = datetime.datetime.now()
end_date = start_date + datetime.timedelta(minutes=RUN_MINUTES)

manager = ts.StrategyManager(
    start_date=start_date,
    end_date=end_date,
    console_mode=True,
)

print(f"Starting MACD+Renko on {SYMBOL} — /exit to stop.")
manager.start(strategy, wait=True)
