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

frame = 1
if frame == 1:
    file_path = os.path.abspath("L:/data/fx/OANDA-Japan MT5 Live/mt5_USDJPY_TickToMIN1.csv")
elif frame < 60:
    file_path = os.path.abspath(f"L:/data/fx/OANDA-Japan MT5 Live/mt5_USDJPY_min{frame}.csv")
else:
    file_path = os.path.abspath(f"L:/data/fx/OANDA-Japan MT5 Live/mt5_USDJPY_h{int(frame/60)}.csv")
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
    ldb = db.LogCSVStorage(f"./runner_test_USDJPY_{frame}_{slope}_{threshold}{brick_param_str}{suffix}.csv")
    storage = db.SQLiteStorage("./runner_test.db", "csv", "back_test", ldb)
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
    runner = ts.StrategyRunner(client.symbols)
    signals = runner.get_signals(st1)
    logger.info(f"total signals: {len(signals)}")
    runner.handle_signals(st1, signals)
    client.close_client()


if __name__ == "__main__":
    # range_function = lambda df: fprocess.regime.range_detection_by_atr(df, mean_window=100, atr_window=14, range_threshold=0.6, ohlc_columns=ohlc_columns)
    range_function = lambda df: fprocess.regime.range_detection_by_bollinger(df,std_window=200, window=20, std_threshold=0.6, ohlc_columns=ohlc_columns)
    trailing_stop = ts.trailingstop.TrailingStopByATR(atr_window=7, atr_multiplier=2.0, ohlc_columns=ohlc_columns, clip_with_price=False)
    # trailing_stop = None
    MACDRenko(0, threshold=2, atr_window=7, range_function=range_function, trailing_stop=trailing_stop)