import unittest, os, sys
import logging

import dotenv

BASE_PATH = os.path.join(os.path.dirname(__file__), "..")
dotenv.load_dotenv(".env")

# for finance_client
module_path = os.path.abspath(f"{BASE_PATH}/../finance_client")
sys.path.append(module_path)
from finance_client import AgentTool, CSVClient
from finance_client.fprocess.fprocess.idcprocess import *

sys.path.append(BASE_PATH)
from trade_strategy import pipeline, signal
import trade_strategy as ts

logger = logging.getLogger("trade_strategy.test")
# enable debug level
logging.basicConfig(level=logging.DEBUG)

data_folder = os.environ["ts_data_folder"]
symbol = "yfinance_1333.T_D1.csv"
file_path = os.path.join(data_folder, symbol)

class Test(unittest.TestCase):
    def test_MACDWidthCSV(self):
        client = CSVClient(files=file_path, auto_step_index=True, start_index=300)
        agent_tool = AgentTool(client)
        # dummy
        strategy = ts.strategies.MACDCross(client, interval_mins=0)
        pipe = pipeline.TradingPipeline(agent_tool.get_ohlc_with_indicators)
        pipe.before_signal(strategy=strategy, symbols=symbol)
        self.assertIn(symbol, strategy.market_trends)
        print(strategy.market_trends[symbol])
        sample_signal = signal.BuySignal(strategy.key, symbol=symbol)
        refined_signal = pipe.after_signal([sample_signal])
        self.assertIsInstance(refined_signal, list)
        self.assertGreaterEqual(len(refined_signal), 0)

if __name__ == "__main__":
    unittest.main()