import unittest, os, sys

import dotenv

BASE_PATH = os.path.join(os.path.dirname(__file__), "..")
# for finance_client
module_path = os.path.abspath(f"{BASE_PATH}/../finance_client")
sys.path.append(module_path)
from finance_client.csv.client import CSVClient
from finance_client.fprocess.fprocess.idcprocess import *

sys.path.append(BASE_PATH)
import trade_strategy as ts

from logging import getLogger
logger = getLogger("trade_strategy.test")

dotenv.load_dotenv(".env")

data_folder = os.environ["ts_data_folder"]
file_path = os.path.join(data_folder, "yfinance_1333.T_D1.csv")


class Test(unittest.TestCase):
    def test_MACDWidthCSV(self):
        client = CSVClient(files=file_path, auto_step_index=True, start_index=300)
        st1 = ts.strategies.MACDCross(client, interval_mins=0)
        manager = ts.ParallelStrategyManager([st1], seconds=10)
        manager.start_strategies()


if __name__ == "__main__":
    unittest.main()
