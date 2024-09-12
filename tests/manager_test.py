import datetime
import os
import re
import sys
import time
import unittest
from logging import DEBUG

import dotenv

module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(module_path)
import trade_strategy as ts
from finance_client.fprocess.fprocess import idcprocess as idp
from finance_client.csv.client import CSVClient
from finance_client.db import SQLiteStorage

dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
data_folder = os.environ["ts_data_folder"]
file_name = os.environ["ts_symbol_file"]
frame = int(os.environ["ts_frame"])
file_path = os.path.join(data_folder, file_name)


class Test(unittest.TestCase):
    # def test_auto_interval_min(self):
    #     storage = SQLiteStorage(database_path="./manager_test.db", provider="csv")
    #     freq_mins = 1
    #     client = CSVClient(files=file_path, frame=freq_mins, storage=storage)
    #     # check if interval min equal to frame/freq of finance_client
    #     st1 = ts.StrategyClient(client, interval_mins=None)

    #     expected_sleep_seconds = 60
    #     manager = ts.StrategyManager(
    #         start_date=datetime.datetime.now(),
    #         end_date=datetime.datetime.now() + datetime.timedelta(seconds=expected_sleep_seconds * 2),
    #         log_level=DEBUG,
    #     )
    #     # manually confirm if strategy run 1 time at least
    #     manager.start(st1)
    #     # confirm if manager run in another thread
    #     started_at = datetime.datetime.now()
    #     time.sleep(expected_sleep_seconds)
    #     manager.end()
    #     end_at = datetime.datetime.now()

    #     slept_seconds = (end_at - started_at).total_seconds()
    #     slept_seconds = int(slept_seconds)
    #     self.assertEqual(expected_sleep_seconds, slept_seconds)

    def test_no_interval_min(self):
        storage = SQLiteStorage(database_path="./manager_test.db", provider="csv")
        client = CSVClient(files=file_path, frame=1, storage=storage)
        st1 = ts.StrategyClient(client, interval_mins=-1)
        manager = ts.StrategyManager(
            start_date=datetime.datetime.now(), end_date=datetime.datetime.now() + datetime.timedelta(seconds=10), log_level=DEBUG
        )
        # manually confirm if strategy end on end_date
        manager.start(st1)

    # def test_parallel_timer(self):
    #     storage = SQLiteStorage(database_path="./manager_test.db", provider="csv")
    #     client = CSVClient(file_paths, frame=3, storage=storage)
    #     strategy1 = ts.StrategyClient(client, interval_mins=1)
    #     strategy2 = ts.StrategyClient(client, interval_mins=2)
    #     strategy3 = ts.StrategyClient(client, interval_mins=3)
    #     sts = [strategy1, strategy2, strategy3]
    #     manager = ts.ParallelStrategyManager(
    #         start_date=datetime.datetime.now(), end_date=datetime.datetime.now() + datetime.timedelta(seconds=60 * 5)
    #     )
    #     manager.start(sts)
    #     time.sleep(60 * 5)

    # def test_MACDCross_Registration(self):
    #     storage = SQLiteStorage(database_path="./manager_test.db", provider="csv")
    #     client = CSVClient(file_paths, frame=frame, storage=storage)
    #     option = {"column": "Close", "short_window": 9, "long_window": 18, "signal_window": 9}
    #     macd = idp.MACDProcess(key="test_macd", option=option)
    #     st1 = ts.strategies.MACDCross(client, interval_mins=-1, macd_process=macd)
    #     manager = ts.StrategyManager(start_date=datetime.datetime.now(), end_date=datetime.datetime.now() + datetime.timedelta(seconds=10))
    #     manager.start(st1)


if __name__ == "__main__":
    unittest.main()
