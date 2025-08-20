import unittest, os, json, sys, datetime

import dotenv

BASE_PATH = os.path.join(os.path.dirname(__file__), "..")
# for finance_client
module_path = os.path.abspath(f"{BASE_PATH}/../finance_client")
sys.path.append(module_path)
import finance_client.fprocess.fprocess.idcprocess as idp
from finance_client.csv.client import CSVClient

sys.path.append(BASE_PATH)
import trade_strategy as ts

from logging import getLogger, config
dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

try:
    with open(os.path.join(BASE_PATH, "trade_strategy/settings.json"), "r") as f:
        settings = json.load(f)
except Exception as e:
    print(f"fail to load settings file: {e}")
    raise e

data_folder = os.environ["ts_data_folder"]
file_path = os.path.join(data_folder, "yfinance_1333.T_D1.csv")

class Test(unittest.TestCase):
    def test_CCICrossCSV(self):
        client = CSVClient(files=file_path, auto_step_index=True, start_index=100)
        cci_process = idp.CCIProcess()
        st1 = ts.strategies.CCICross(client, cci_process, 0)
        manager = ts.ParallelStrategyManager([st1], seconds=10)
        manager.start_strategies()

    def test_CCIBoaderCSV(self):
        client = CSVClient(files=file_path, auto_step_index=True, start_index=100)
        cci_process = idp.CCIProcess()
        st1 = ts.strategies.CCIBoader(client, cci_process, 100, -100, 0)
        manager = ts.ParallelStrategyManager([st1], seconds=10)
        manager.start_strategies()


if __name__ == "__main__":
    unittest.main()
