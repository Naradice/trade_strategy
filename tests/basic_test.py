import os
import re
import sys
import time
import unittest

import dotenv

BASE_PATH = os.path.join(os.path.dirname(__file__), "..")
# for finance_client
module_path = os.path.abspath(f"{BASE_PATH}/../finance_client")
sys.path.append(module_path)
import finance_client.fprocess.fprocess.idcprocess as idp
from finance_client.csv.client import CSVClient

# for trade_strategy
module_path = os.path.abspath(BASE_PATH)
sys.path.append(module_path)
import trade_strategy as ts

dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
data_folder = os.environ["ts_data_folder"]
file_name_format = os.environ["ts_symbol_file"]
frame = int(os.environ["ts_frame"])


def replace_variables(text, replacement):
    pattern = r"\$(.*?)\$"
    replaced_text = re.sub(pattern, replacement, text)
    return replaced_text


symbols = ["1333.T"]
file_paths = [os.path.join(data_folder, replace_variables(file_name_format, symbol)) for symbol in symbols]


class Test(unittest.TestCase):
    def test_strategy_base(self):
        client = CSVClient(file_paths, frame=frame)
        ts.StrategyClient(client, interval_mins=-1)

    def test_auto_interval_min(self):
        client = CSVClient(files=file_paths[0], frame=1)
        st1 = ts.StrategyClient(client, interval_mins=None)
        manager = ts.ParallelStrategyManager([st1], seconds=10)

    def test_parallel_timer(self):
        client = CSVClient(file_paths, frame=3)
        strategy1 = ts.StrategyClient(client, interval_mins=1)
        strategy2 = ts.StrategyClient(client, interval_mins=2)
        strategy3 = ts.StrategyClient(client, interval_mins=3)
        sts = [strategy1, strategy2, strategy3]
        manager = ts.ParallelStrategyManager(sts, minutes=5)
        manager.start_strategies()
        time.sleep(3)
        manager.stop_strategies()

    def test_MACDCross_Registration(self):
        client = CSVClient(file_paths, frame=frame)
        st1 = ts.strategies.MACDCross(client, interval_mins=-1)
        option = {"column": "Close", "short_window": 9, "long_window": 18, "signal_window": 9}
        macd = idp.MACDProcess(key="test_macd", option=option)
        st2 = ts.strategies.MACDCross(client, macd, interval_mins=-1)
        sts = [st1, st2]
        manager = ts.ParallelStrategyManager(sts, minutes=5)


if __name__ == "__main__":
    unittest.main()
