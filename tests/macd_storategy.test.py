import unittest, os, json, sys, datetime

finance_module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../modules"))
sys.path.append(finance_module_path)
from finance_client.client_base import Client
from finance_client.csv.client import CSVClient
from finance_client.fprocess.idcprocess import *

module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(module_path)
import trade_strategy as ts

csv_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "L:/data/csv/bitcoin_5_2017T0710-2021T103022.csv"))


class Test(unittest.TestCase):
    def test_create_order(self):
        client = CSVClient(files=csv_file, date_column="Timestamp", start_index=100)
        st1 = ts.strategies.MACDCross(client)
        st1.get_signal(client.get_ohlc(100), 0)


if __name__ == "__main__":
    unittest.main()
