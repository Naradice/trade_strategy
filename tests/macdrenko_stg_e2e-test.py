import unittest, os, json, sys

import dotenv

BASE_PATH = os.path.join(os.path.dirname(__file__), "..")
# for finance_client
module_path = os.path.abspath(f"{BASE_PATH}/../finance_client")
sys.path.append(module_path)
from finance_client.csv.client import CSVClient
from finance_client.fprocess.fprocess.idcprocess import *

sys.path.append(BASE_PATH)
import trade_strategy as ts

from logging import getLogger, config

try:
    with open(os.path.join(BASE_PATH, "trade_strategy/settings.json"), "r") as f:
        settings = json.load(f)
except Exception as e:
    print(f"fail to load settings file: {e}")
    raise e
dotenv.load_dotenv(".env")

data_folder = os.environ["ts_data_folder"]
base_path = os.path.dirname(__file__)
date_column = "Datetime"
symbols = ["1333.T", "1332.T", "1605.T"]
file_paths = [f"{data_folder}/yfinance_{symbol}_D1.csv" for symbol in symbols]


class Test(unittest.TestCase):
    def test_MACDWidthCSV1D(self):
        frame = 60 * 24
        ohlc_columns = ["Open", "High", "Low", "Close"]

        client = CSVClient(
            files=file_paths[0],
            auto_step_index=True,
            frame=frame,
            start_index=130,
            columns=ohlc_columns,
            date_column=date_column,
            slip_type="percent",
            do_render=False,
        )
        columns = client.get_ohlc_columns()
        macd_p = MACDProcess(short_window=12, long_window=26, signal_window=9, target_column=ohlc_columns[3])
        renko_p = RenkoProcess(window=60)
        rtp_p = RangeTrendProcess(slope_window=3)
        bband_process = BBANDProcess(target_column=columns["Close"], alpha=2)
        st1 = ts.strategies.MACDRenkoRangeSLByBB(
            client, renko_p, macd_p, bband_process, rtp_p, slope_window=5, interval_mins=0, data_length=70
        )
        manager = ts.ParallelStrategyManager([st1], seconds=5)
        manager.start_strategies()


if __name__ == "__main__":
    unittest.main()
