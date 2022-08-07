import unittest, os, json, sys, datetime

finance_module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../modules'))
sys.path.append(finance_module_path)
from finance_client.client_base import Client
from finance_client.csv.client import CSVClient
from finance_client.utils.idcprocess import *

module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(module_path)
import trade_storategy as ts

csv_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data_source/bitcoin_5_2017T0710-2021T103022.csv'))

class Test(unittest.TestCase):
    
    def test_create_order(self):
        client = CSVClient(file=csv_file)
        st1 = ts.storategies.MACDCross(client)
        st1.create_signal()
    
if __name__ == '__main__':
    unittest.main()