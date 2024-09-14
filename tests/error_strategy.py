import os
import sys

module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(module_path)
from trade_strategy import StrategyClient


class SlopeChange(StrategyClient):
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
