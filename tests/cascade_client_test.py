import unittest, os, json, sys, datetime

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
log_path = f'./{log_file_base_name}_ccistg_test_{datetime.datetime.now(datetime.UTC).strftime("%Y%m%d")}.logs'
logger_config["handlers"]["fileHandler"]["filename"] = log_path
config.dictConfig(logger_config)
logger = getLogger("trade_strategy.test")

file_path = os.path.abspath("L:/data/fx/OANDA-Japan MT5 Live/mt5_USDJPY_min5.csv")


class Test(unittest.TestCase):
    def test_MACDCrossCSV(self):
        frames = [10, 120]
        client = CSVClient(file_path, auto_step_index=True, start_index=2000, logger=logger, symbols=["USDJPY"])
        ohlc_columns = client.get_ohlc_columns()
        macd_process = MACDProcess(target_column=ohlc_columns["Close"])
        st1 = ts.strategies.MACDCross(client, macd_process, 0, data_length=1000, logger=logger)
        st_client = ts.CascadeStrategyClient(st1, frames, logger)
        start_date = datetime.datetime.now()
        manager = ts.StrategyManager(start_date=start_date, end_date=start_date + datetime.timedelta(seconds=60), logger=logger)
        manager.start(st_client)

    def test_multi_strategies(self):
        frames = [30, 120]
        client = CSVClient(file_path, auto_step_index=True, start_index=2000, logger=logger, symbols=["USDJPY"])
        ohlc_columns = client.get_ohlc_columns()
        cci_process = CCIProcess(ohlc_column=[ohlc_columns["Open"], ohlc_columns["High"], ohlc_columns["Low"], ohlc_columns["Close"]])
        st1 = ts.strategies.CCICross(client, cci_process, interval_mins=0)
        macd_process = MACDProcess(target_column=ohlc_columns["Close"])
        st2 = ts.strategies.MACDCross(client, macd_process, 0, data_length=1000, logger=logger)
        st_client = ts.CascadeStrategyClient([st1, st2], frames, logger)
        start_date = datetime.datetime.now()
        manager = ts.StrategyManager(start_date=start_date, end_date=start_date + datetime.timedelta(seconds=60), logger=logger)
        manager.start(st_client)


if __name__ == "__main__":
    unittest.main()
