import json
import os
import sys

base_path = os.path.dirname(__file__)
module_path = os.path.abspath(os.path.join(base_path, ".."))
sys.path.append(module_path)
import trade_strategy as ts
import trade_strategy.signal_trade as signal_trade
from finance_client.csv.client import CSVClient
from finance_client.fprocess.fprocess.idcprocess import *


with open(os.path.join(base_path, "stock_codes.json")) as fp:
    nikkei_codes = json.load(fp)
base_path = os.path.dirname(__file__)
file_paths = [os.path.abspath(os.path.abspath(os.path.join(base_path, f"L:/data/yfinance/yfinance_{symbol}_D1.csv"))) for symbol in nikkei_codes]
frame = 60 * 24
date_column = "Datetime"
ohlc_columns = ["Open", "High", "Low", "Adj Close"]


class GetSignalTest:
    def test_get_sygnal_with_arbitrary_client(self):
        observation_length = 100
        slope_window = 3
        client = CSVClient(files=file_paths, columns=ohlc_columns, date_column=date_column, start_index=observation_length)
        macd_p = MACDProcess(short_window=12, long_window=26, signal_window=9, target_column=ohlc_columns[3])
        renko_p = RenkoProcess(window=30, ohlc_column=ohlc_columns)
        macd_slope = SlopeProcess(key="m", target_column=macd_p.KEY_MACD, window=slope_window)
        signal_slope = SlopeProcess(key="s", target_column=macd_p.KEY_SIGNAL, window=slope_window)

        signals = signal_trade.list_signals(
            client,
            ts.strategies.MACDRenko.key,
            observation_length,
            nikkei_codes,
            idc_processes=[macd_p, renko_p, macd_slope, signal_slope],
            signal_file_path="./arbital_client_test_signls.json",
        )
        signal_trade.order_by_signals(signals, client, "random")


if __name__ == "__main__":
    st = GetSignalTest()
    st.test_get_sygnal_with_arbitrary_client()
