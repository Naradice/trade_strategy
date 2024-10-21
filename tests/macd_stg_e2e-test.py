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
log_path = f'./{log_file_base_name}_macdstg_test_{datetime.datetime.now(datetime.UTC).strftime("%Y%m%d%H")}.logs'
logger_config["handlers"]["fileHandler"]["filename"] = log_path
config.dictConfig(logger_config)
logger = getLogger("trade_strategy.test")


class Test(unittest.TestCase):
    def test_MACDWidthCSV(self):
        client = CSVClient(files="L:/data/csv/bitcoin_5_2017T0710-2021T103022.csv", auto_step_index=True, start_index=750, logger=logger)
        st1 = ts.strategies.MACDCross(client, interval_mins=-1, logger=logger)
        start_date = datetime.datetime.now()
        manager = ts.StrategyManager(start_date=start_date, end_date=start_date + datetime.timedelta(seconds=180), logger=logger)
        manager.start(st1)


if __name__ == "__main__":
    unittest.main()
