import datetime
import os
import signal
import sys
import time
import unittest
from logging import DEBUG, INFO

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
console_mode = True


class ErrorClient(ts.StrategyClient):
    key = "error_test_client"

    def __init__(
        self,
        finance_client,
        idc_processes=...,
        interval_mins: int = -1,
        amount=1,
        data_length: int = 100,
        save_signal_info=False,
        logger=None,
    ) -> None:
        super().__init__(finance_client, idc_processes, interval_mins, amount, data_length, save_signal_info, logger)

    @classmethod
    def get_required_idc_param_keys(self):
        return {}

    def get_signal(self, df, long_short: int = None, symbols=...):
        raise Exception("test client for error case")
        return None


class InteraptManager(ts.StrategyManager):
    def __init__(self, start_date, end_date, logger=None, log_level=..., console_mode=True) -> None:
        super().__init__(start_date, end_date, logger, log_level, console_mode)

    def start(self, strategy: ts.StrategyClient, sleep_seconds=10):
        super().start(strategy)
        self.logger.debug("start sleeping")
        time.sleep(sleep_seconds)
        os.kill(os.getpid(), signal.SIGINT)


class Test(unittest.TestCase):
    def test_auto_interval_min_with_sleep(self):
        storage = SQLiteStorage(database_path="./manager_test.db", provider="csv")
        freq_mins = 1
        client = CSVClient(files=file_path, frame=freq_mins, storage=storage)
        # check if interval min equal to frame/freq of finance_client
        st1 = ts.StrategyClient(client, interval_mins=None)

        expected_sleep_seconds = 60
        manager = ts.StrategyManager(
            start_date=datetime.datetime.now(),
            end_date=datetime.datetime.now() + datetime.timedelta(seconds=expected_sleep_seconds * 2),
            log_level=DEBUG,
            console_mode=console_mode,
        )
        # manually confirm if strategy run 1 time at least
        started_at = datetime.datetime.now()
        manager.start(st1, wait=False)
        # confirm if manager run in another thread
        time.sleep(expected_sleep_seconds)
        manager.end()
        end_at = datetime.datetime.now()

        slept_seconds = (end_at - started_at).total_seconds()
        slept_seconds = int(slept_seconds)
        # if strategy run in the same thread, it would run in main thread till end_date
        # We add 5 seconds since sometimes it takes seconds to end manager.
        self.assertLessEqual(expected_sleep_seconds, slept_seconds + 5)

    def test_auto_interval_min(self):
        storage = SQLiteStorage(database_path="./manager_test.db", provider="csv")
        freq_mins = 1
        client = CSVClient(files=file_path, frame=freq_mins, storage=storage)
        # check if interval min equal to frame/freq of finance_client
        st1 = ts.StrategyClient(client, interval_mins=None)

        running_seconds = 60
        start_date = datetime.datetime.now()
        end_date = start_date + datetime.timedelta(seconds=running_seconds)
        manager = ts.StrategyManager(
            start_date=start_date,
            end_date=end_date,
            log_level=DEBUG,
            console_mode=console_mode,
        )
        manager.start(st1, wait=True)
        end_at = datetime.datetime.now()
        diff_seconds = (end_date - end_at).total_seconds()
        # if strategy run in the same thread, it would run in main thread till end_date
        self.assertLessEqual(diff_seconds, 3)

    def test_no_interval_min(self):
        storage = SQLiteStorage(database_path="./manager_test.db", provider="csv")
        client = CSVClient(files=file_path, frame=1, storage=storage)
        st1 = ts.StrategyClient(client, interval_mins=-1)
        manager = ts.StrategyManager(
            start_date=datetime.datetime.now(),
            end_date=datetime.datetime.now() + datetime.timedelta(seconds=30),
            log_level=DEBUG,
            console_mode=console_mode,
        )
        manager.start(st1, wait=True)

    def test_parallel_timer(self):
        storage = SQLiteStorage(database_path="./manager_test.db", provider="csv")
        client = CSVClient(file_path, frame=1, storage=storage)
        strategy1 = ts.StrategyClient(client, interval_mins=1)
        strategy2 = ts.StrategyClient(client, interval_mins=2)
        strategy3 = ts.StrategyClient(client, interval_mins=3)
        sts = [strategy1, strategy2, strategy3]
        manager = ts.ParallelStrategyManager(
            start_date=datetime.datetime.now(),
            end_date=datetime.datetime.now() + datetime.timedelta(seconds=60 * 5),
            log_level=DEBUG,
            console_mode=console_mode,
        )
        # manually confirm if strategy start parallelly as expected
        manager.start(sts, wait=True)

    def test_MACDCross_Registration(self):
        storage = SQLiteStorage(database_path="./manager_test.db", provider="csv")
        client = CSVClient(file_path, frame=frame, storage=storage)
        option = {"column": "close", "short_window": 9, "long_window": 18, "signal_window": 9}
        macd = idp.MACDProcess(key="test_macd", option=option)
        st1 = ts.strategies.MACDCross(client, interval_mins=-1, macd_process=macd)
        manager = ts.StrategyManager(
            start_date=datetime.datetime.now(), end_date=datetime.datetime.now() + datetime.timedelta(seconds=30), console_mode=console_mode
        )
        try:
            manager.start(st1)
        except KeyboardInterrupt:
            pass
        except Exception as e:
            self.fail(f"test_MACDCross_Registration failed: {e}")

    def test_close_manager_by_error(self):
        storage = SQLiteStorage(database_path="./manager_test.db", provider="csv")
        client = CSVClient(files=file_path, frame=1, storage=storage)
        st1 = ErrorClient(client, interval_mins=-1)
        running_seconds = 60
        start_date = datetime.datetime.now()
        end_date = datetime.datetime.now() + datetime.timedelta(seconds=running_seconds)
        manager = ts.StrategyManager(
            start_date=start_date,
            end_date=end_date,
            log_level=DEBUG,
            console_mode=console_mode,
        )
        start_at = datetime.datetime.now()
        manager.start(st1)
        end_at = datetime.datetime.now()
        delta = end_at - start_at
        # error client raise an error when strategy get a signal. as it stops the strategy immedeately
        self.assertLess(delta.total_seconds(), 10)
        self.assertGreater(end_date, end_at)

    def test_zzz_auto_interval_min(self):
        storage = SQLiteStorage(database_path="./manager_test.db", provider="csv")
        freq_mins = 1
        client = CSVClient(files=file_path, frame=freq_mins, storage=storage)
        st1 = ts.StrategyClient(client, interval_mins=-1)
        running_seconds = 30
        start_date = datetime.datetime.now()
        end_date = start_date + datetime.timedelta(seconds=running_seconds)
        manager = InteraptManager(
            start_date=start_date,
            end_date=end_date,
            log_level=DEBUG,
            console_mode=console_mode,
        )
        sleep_second_till_error = 10
        start_at = datetime.datetime.now()
        manager.start(st1, sleep_seconds=sleep_second_till_error)
        end_at = datetime.datetime.now()
        actual_diff = int((end_at - start_at).total_seconds())
        # if strategy thread was running in another thead even if KeyboardException happened, actual diff would be greater than expected
        self.assertLessEqual(actual_diff, sleep_second_till_error)
        self.assertTrue(manager.stop_event.is_set())


if __name__ == "__main__":
    unittest.main()
