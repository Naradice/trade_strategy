import unittest, os, sys

import dotenv

BASE_PATH = os.path.join(os.path.dirname(__file__), "..")
# for finance_client
module_path = os.path.abspath(f"{BASE_PATH}/../finance_client")
sys.path.append(module_path)
from finance_client.csv.client import CSVClient
from finance_client.fprocess.fprocess.idcprocess import *
from finance_client.config import AccountRiskConfig
from finance_client.risk_manager import create_atr_option, create_fixed_loss_option, create_percent_equity_option

sys.path.append(BASE_PATH)
import trade_strategy as ts

from logging import getLogger
logger = getLogger("trade_strategy.test")

dotenv.load_dotenv(".env")

data_folder = os.environ["ts_data_folder"]
file_path = os.path.join(data_folder, "yfinance_1333.T_D1.csv")
fx_file_path = os.path.join(data_folder, "..\\fx\\OANDA-Japan MT5 Live\\mt5_USDJPY_min30.csv")


class Test(unittest.TestCase):
    def test_MACDWithCSVWithATRRiskOption(self):
        if os.path.exists("./finance_client.db"):
            os.remove("./finance_client.db")
        ohlc_columns=["open", "high", "low", "close"]
        risk_config = AccountRiskConfig(
            base_currency="JPY",
            max_single_trade_percent=3.0,
            max_total_risk_percent=10.0,
            daily_max_loss_percent=None,
            allow_aggressive_mode=False,
            aggressive_multiplier=1.5,
            enforce_volume_reduction=True,
            atr_ratio_min_stop_loss=1.0,
        )
        atr_risk_option= create_atr_option(percent=1.0, atr_window=14, atr_multiplier=3.0, ohlc_columns=ohlc_columns, rr_ratio=2.0)
        client = CSVClient(files=fx_file_path, symbols=["USDJPY"], frame=30, date_column="time",
                           auto_step_index=True, start_index=300, risk_option=atr_risk_option, account_risk_config=risk_config)
        st1 = ts.strategies.MACDCross(client, interval_mins=0, trailing_stop=None, volume=None, ohlc_columns=ohlc_columns)
        manager = ts.ParallelStrategyManager([st1], seconds=1000)
        manager.start_strategies()


if __name__ == "__main__":
    unittest.main()
