import os, json, sys, datetime

module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(module_path)
import trade_strategy as ts
from finance_client.csv.client import CSVClient
from finance_client.fprocess.fprocess.idcprocess import *

from logging import getLogger, config

try:
    with open(os.path.join(module_path, "trade_strategy/settings.json"), "r") as f:
        settings = json.load(f)
except Exception as e:
    print(f"fail to load settings file: {e}")
    raise e
logger_config = settings["log"]
log_file_base_name = logger_config["handlers"]["fileHandler"]["filename"]
log_path = f'./{log_file_base_name}_ccistg_test_{datetime.datetime.utcnow().strftime("%Y%m%d")}.logs'
logger_config["handlers"]["fileHandler"]["filename"] = log_path
config.dictConfig(logger_config)
logger = getLogger("trade_strategy.test")

file_path = os.path.abspath("L:/data/fx/OANDA-Japan MT5 Live/mt5_USDJPY_min30.csv")


def test_MACDCrossCSV():
    frames = [30, 60, 240, 480]
    client = CSVClient(file_path, auto_step_index=True, start_index=2000, logger=logger, symbols=["USDJPY"])
    ohlc_columns = client.get_ohlc_columns()
    macd_process = MACDProcess(target_column=ohlc_columns["Close"])
    st1 = ts.strategies.MACDCross(client, macd_process, 0, data_length=1000, logger=logger)
    st_client = ts.CascadeStrategyClient(st1, frames, logger)
    manager = ts.ParallelStrategyManager([st_client], minutes=240, logger=logger)
    manager.start_strategies()


def test_MACDRenko():
    frames = [30, 240]
    client = CSVClient(file_path, auto_step_index=True, start_index=2000, logger=logger, symbols=["USDJPY"])
    ohlc_columns = client.get_ohlc_columns()
    macd_p = MACDProcess(short_window=12, long_window=26, signal_window=9, target_column=ohlc_columns["Close"])
    renko_p = RenkoProcess(window=14, ohlc_column=[ohlc_columns["Open"], ohlc_columns["High"], ohlc_columns["Low"], ohlc_columns["Close"]])
    st = ts.strategies.MACDRenko(client, renko_p, macd_p, slope_window=2, interval_mins=0, data_length=500, threshold=1, logger=logger)
    st_client = ts.CascadeStrategyClient(st, frames, logger)
    manager = ts.ParallelStrategyManager([st_client], minutes=240, logger=logger)
    manager.start_strategies()


if __name__ == "__main__":
    test_MACDRenko()
