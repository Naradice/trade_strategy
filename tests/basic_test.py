import unittest, os, json, sys, datetime

module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(module_path)
import trade_strategy as ts
from finance_client.client_base import Client
from finance_client.csv.client import CSVClient
from finance_client.fprocess.fprocess.idcprocess import *


class Test(unittest.TestCase):
    def test_property(self):
        ts.LongTrend != ts.ShortTrend
        self.assertEqual(ts.LongTrend, ts.LongTrend)

    def test_strategy_base(self):
        client = Client()
        ts.StrategyClient(client, 1)

    def test_parallel_timer(self):
        client = Client()
        strategy1 = ts.StrategyClient(client, 1)
        strategy2 = ts.StrategyClient(client, 2)
        strategy3 = ts.StrategyClient(client, 3)
        sts = [strategy1, strategy2, strategy3]
        manager = ts.ParallelStrategyManager(sts, minutes=5)
        manager.start_strategies()

    def test_MACDCross_Registration(self):
        client = Client()
        st1 = ts.strategies.MACDCross(client, 2)
        option = {"column": "Close", "short_window": 9, "long_window": 18, "signal_window": 9}
        macd = MACDpreProcess(key="test_macd", option=option)
        st2 = ts.strategies.MACDCross(client, 3)
        sts = [st1, st2]
        manager = ts.ParallelStrategyManager(sts, minutes=5)


if __name__ == "__main__":
    unittest.main()
