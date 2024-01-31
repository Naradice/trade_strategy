import unittest, os, json, sys, datetime

module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(module_path)
import trade_strategy as ts
from finance_client.client_base import Client
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
log_path = f'./{log_file_base_name}_mrenko_test_{datetime.datetime.utcnow().strftime("%Y%m%d%H")}.logs'
logger_config["handlers"]["fileHandler"]["filename"] = log_path
config.dictConfig(logger_config)
logger = getLogger("trade_strategy.test")

base_path = os.path.dirname(__file__)
date_column = "Datetime"
symbols = ["1333.T", "1332.T", "1605.T"]
file_paths = [f"L:/data/yfinance/yfinance_{symbol}_D1.csv" for symbol in symbols]


class Test(unittest.TestCase):
    def test_MACDWidthCSV1D(self):
        frame = 60 * 24
        ohlc_columns = ["Open", "High", "Low", "Close"]

        client = CSVClient(
            files=file_paths[0],
            auto_step_index=True,
            frame=frame,
            start_index=130,
            logger=logger,
            columns=ohlc_columns,
            date_column=date_column,
            slip_type="percentage",
            do_render=False,
        )
        columns = client.get_ohlc_columns()
        macd_p = MACDProcess(short_window=12, long_window=26, signal_window=9, target_column=ohlc_columns[3])
        renko_p = RenkoProcess(window=60)
        rtp_p = RangeTrendProcess(slope_window=3)
        bband_process = BBANDProcess(target_column=columns["Close"], alpha=2)
        st1 = ts.strategies.MACDRenkoRangeSLByBB(
            client, renko_p, macd_p, bband_process, rtp_p, slope_window=5, interval_mins=0, data_length=70, logger=logger
        )
        manager = ts.ParallelStrategyManager([st1], minutes=1, logger=logger)
        manager.start_strategies()

    def test_MACDWidthCSV1DSymbols(self):
        stgs = []
        frame = 60 * 24
        ohlc_columns = ["Open", "High", "Low", "Close"]
        for path in file_paths:
            client = CSVClient(
                files=path,
                auto_step_index=True,
                frame=frame,
                start_index=60,
                logger=logger,
                columns=ohlc_columns,
                date_column=date_column,
                slip_type="percentage",
            )
            macd_p = MACDProcess(short_window=6, long_window=13, signal_window=5, target_column=ohlc_columns[3])
            renko_p = RenkoProcess(window=30)
            st = ts.strategies.MACDRenko(client, renko_p, macd_p, slope_window=3, interval_mins=0, data_length=30, logger=logger)
            stgs.append(st)
        manager = ts.MultiSymbolStrategyManager(stgs, minutes=3, logger=logger)
        manager.start_strategies()


if __name__ == "__main__":
    unittest.main()
