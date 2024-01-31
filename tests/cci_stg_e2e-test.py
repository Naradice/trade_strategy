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
log_path = f'./{log_file_base_name}_ccistg_test_{datetime.datetime.utcnow().strftime("%Y%m%d")}.logs'
logger_config["handlers"]["fileHandler"]["filename"] = log_path
config.dictConfig(logger_config)
logger = getLogger("trade_strategy.test")

file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data_source/bitcoin_5_2017T0710-2021T103022.csv"))


class Test(unittest.TestCase):
    def test_CCICrossCSV(self):
        client = CSVClient(file=file_path, auto_step_index=True, start_index=7500, logger=logger)
        cci_process = CCIProcess()
        st1 = ts.strategies.CCICross(client, cci_process, 0, logger=logger)
        manager = ts.ParallelStrategyManager([st1], minutes=5, logger=logger)
        manager.start_strategies()

    def test_CCIBoaderCSV(self):
        client = CSVClient(file=file_path, auto_step_index=True, start_index=7500, logger=logger)
        cci_process = CCIProcess()
        st1 = ts.strategies.CCIBoader(client, cci_process, 100, -100, 0, logger=logger)
        manager = ts.ParallelStrategyManager([st1], minutes=5, logger=logger)
        manager.start_strategies()


if __name__ == "__main__":
    unittest.main()
