import os, json, sys, datetime


module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(module_path)
import trade_strategy as ts
from finance_client.csv.client import CSVClient
from finance_client import db
from finance_client.fprocess.fprocess.idcprocess import *
from finance_client import fprocess

from logging import getLogger, config

try:
    with open(os.path.join(module_path, "trade_strategy/settings.json"), "r") as f:
        settings = json.load(f)
except Exception as e:
    print(f"fail to load settings file: {e}")
    raise e
logger_config = settings["log"]
log_file_base_name = logger_config["handlers"]["fileHandler"]["filename"]
log_path = f'./{log_file_base_name}_mrenko_{datetime.datetime.now().strftime("%Y%m%d")}.log'
logger_config["handlers"]["fileHandler"]["filename"] = log_path
config.dictConfig(logger_config)
logger = getLogger("trade_strategy.back_test")

file_path = os.path.abspath("L:/data/fx/OANDA-Japan MT5 Live/mt5_USDJPY_h1.csv")
frame = 60
date_column = "time"
ohlc_columns = ["open", "high", "low", "close"]


def MACDRenko(slope=5, threshold=2, atr_window=None, brick_size=None, range_function=None, trailing_stop=None):
    additionals = []
    if range_function is not None:
        additionals.append("range")
    if trailing_stop is not None:
        additionals.append("tstop")

    suffix = "_".join(additionals)
    if suffix != "":
        suffix = "_" + suffix
    brick_param_str = f"_{brick_size}" if brick_size is not None else f"_{atr_window}"
    ldb = db.LogCSVStorage(f"./back_test_USDJPY_{frame}_{slope}_{threshold}{brick_param_str}{suffix}.csv")
    storage = db.SQLiteStorage("./back_test.db", "csv", "back_test", ldb)
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
    if brick_size is not None:
        renko_p = RenkoProcess(brick_size=brick_size, ohlc_column=ohlc_columns)
    else:
        renko_p = RenkoProcess(window=atr_window, ohlc_column=ohlc_columns)
    st1 = ts.strategies.MACDRenko(client, renko_p, macd_p, slope_window=slope,
                                  interval_mins=0, data_length=100, logger=logger, threshold=threshold,
                                  range_function=range_function, trailing_stop=trailing_stop)
    manager = ts.ParallelStrategyManager([st1], minutes=10, logger=logger, result_csv_path="./macd_renko_result.csv")
    manager.start_strategies()


def MACDRenkoByBBCSV(slope=5, window=20):
    ldb = db.LogCSVStorage(f"./back_test_USDJPY_{frame}.csv")
    storage = db.SQLiteStorage("./back_test.db", "csv", "back_test", ldb)
    client = CSVClient(
        files=file_path,
        auto_step_index=True,
        frame=frame,
        start_index=250,
        columns=ohlc_columns,
        date_column=date_column,
        slip_type="percent",
        storage=storage,
    )
    columns = client.get_ohlc_columns()

    bband_process = BBANDProcess(target_column=columns["Close"], window=window)
    macd_p = MACDProcess(short_window=12, long_window=26, signal_window=9, target_column=ohlc_columns[3])
    renko_p = RenkoProcess(window=60, ohlc_column=ohlc_columns)
    # BBAN std require 200 for data length
    st1 = ts.strategies.MACDRenkoSLByBB(client, renko_p, macd_p, slope_window=slope, bolinger_process=bband_process,
                                         interval_mins=0, data_length=250, logger=logger)
    manager = ts.ParallelStrategyManager([st1], minutes=10, logger=logger)
    manager.start_strategies()

def MACDRenkoRangeCSV(slope=5):
    ldb = db.LogCSVStorage(f"./back_test_USDJPY_{frame}.csv")
    storage = db.SQLiteStorage("./back_test.db", "csv", "back_test", ldb)
    client = CSVClient(
        files=file_path,
        auto_step_index=True,
        frame=frame,
        start_index=150,
        columns=ohlc_columns,
        date_column=date_column,
        slip_type="percent",
        do_render=False,
        storage=storage
    )
    macd_p = MACDProcess(short_window=12, long_window=26, signal_window=9, target_column=ohlc_columns[3])
    renko_p = RenkoProcess(window=60, ohlc_column=ohlc_columns)
    rtp_p = RangeTrendProcess(slope_window=3)
    st1 = ts.strategies.MACDRenkoRange(client, renko_p, macd_p, rtp_p, slope_window=slope, interval_mins=0, data_length=120, logger=logger)
    manager = ts.ParallelStrategyManager([st1], minutes=10, logger=logger)
    manager.start_strategies()


def MACDRenkoRangeSLCSV(slope_window=5, use_tp=True):
    ldb = db.LogCSVStorage(f"./back_test_USDJPY_{frame}.csv")
    storage = db.SQLiteStorage("./back_test.db", "csv", "back_test", ldb)
    client = CSVClient(
        files=file_path,
        auto_step_index=True,
        frame=frame,
        start_index=150,
        columns=ohlc_columns,
        date_column=date_column,
        slip_type="percent",
        do_render=False,
        storage=storage
    )
    columns = client.get_ohlc_columns()
    macd_p = MACDProcess(short_window=12, long_window=26, signal_window=9, target_column=ohlc_columns[3])
    renko_p = RenkoProcess(window=60, ohlc_column=ohlc_columns)
    rtp_p = RangeTrendProcess(slope_window=3)
    bband_process = BBANDProcess(target_column=columns["Close"], alpha=2)
    st1 = ts.strategies.MACDRenkoRangeSLByBB(
        client, renko_p, macd_p, bband_process, rtp_p, slope_window=slope_window, interval_mins=0, data_length=120, use_tp=use_tp, logger=logger,
        alpha=4, bolinger_threshold=2
    )
    manager = ts.ParallelStrategyManager([st1], minutes=10, logger=logger)
    manager.start_strategies()


if __name__ == "__main__":
    range_function = lambda df: fprocess.regime.range_detection_by_atr(df, mean_window=100, atr_window=14, range_threshold=0.6, ohlc_columns=ohlc_columns)
    # range_function = lambda df: fprocess.regime.range_detection_by_bollinger(df,std_window=200, window=20, std_threshold=0.6, ohlc_columns=ohlc_columns)
    # range_function = None
    trailing_stop = ts.trailingstop.TrailingStopByATR(atr_window=14, atr_multiplier=1.0, ohlc_columns=ohlc_columns)
    # trailing_stop = None
    MACDRenko(0, threshold=1, brick_size=0.3, range_function=range_function, trailing_stop=trailing_stop)
    # MACDRenkoByBBCSV(slope=5, window=14)
    # MACDRenkoRangeCSV(slope=2)
    # MACDRenkoRangeSLCSV(slope_window=2, use_tp=False)
