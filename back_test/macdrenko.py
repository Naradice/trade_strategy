import os, json, sys, datetime
module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(module_path)
import trade_storategy as ts
from finance_client.csv.client import CSVClient
from finance_client.mt5 import MT5Client
from finance_client.utils.idcprocess import *

from logging import getLogger, config
try:
    with open(os.path.join(module_path, 'trade_storategy/settings.json'), 'r') as f:
        settings = json.load(f)
except Exception as e:
    print(f"fail to load settings file: {e}")
    raise e
logger_config = settings["log"]
log_file_base_name = logger_config["handlers"]["fileHandler"]["filename"]
log_path = f'./{log_file_base_name}_mrenko_{datetime.datetime.utcnow().strftime("%Y%m%d%H")}.logs'
logger_config["handlers"]["fileHandler"]["filename"] = log_path
config.dictConfig(logger_config)
logger = getLogger("trade_storategy.back_test")

# file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../stocknet/finance_client/finance_client/data_source/csv/USDJPY_forex_min30.csv'))
# date_column = "Time"
file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../stocknet/finance_client/finance_client/data_source/mt5/OANDA-Japan MT5 Live/mt5_USDJPY_min30.csv'))
date_column = "time"
ohlc_columns = ["open", "high", "low", "close"]

def MACDRenkoByBBCSV():
    client = CSVClient(file=file_path, auto_step_index=True, start_index=0, logger=logger, columns=ohlc_columns, date_column=date_column, slip_type="percentage")
    columns = client.get_ohlc_columns()
    macd_p = MACDpreProcess(short_window=12, long_window=26, signal_window=9, target_column=ohlc_columns[3])
    renko_p = RenkoProcess(window=60, date_column=columns["Time"])
    st1 = ts.storategies.MACDRenko(client, renko_p, macd_p, slope_window = 5, interval_mins = 0, data_length=120, logger=logger)
    manager = ts.ParallelStorategyManager([st1], minutes=30, logger=logger)
    manager.start_storategies()

def MACDRenkoRangeCSV():
    client = CSVClient(file=file_path, auto_step_index=True, start_index=0, logger=logger, columns=ohlc_columns ,date_column=date_column, slip_type="percentage", auto_refresh_index=False, do_render=False)
    columns = client.get_ohlc_columns()
    macd_p = MACDpreProcess(short_window=12, long_window=26, signal_window=9, target_column=ohlc_columns[3])
    renko_p = RenkoProcess(window=60, date_column=columns["Time"], ohlc_column=ohlc_columns)
    rtp_p = RangeTrendProcess(slope_window=3)
    st1 = ts.storategies.MACDRenkoRange(client, renko_p, macd_p, rtp_p, slope_window = 5, interval_mins = 0, data_length=70, logger=logger)
    manager = ts.ParallelStorategyManager([st1], minutes=60*3, logger=logger)
    manager.start_storategies()
    
def MACDRenkoRangeSLCSV():
    client = CSVClient(file=file_path, auto_step_index=True, start_index=0, logger=logger, columns=ohlc_columns ,date_column=date_column, slip_type="percentage", auto_refresh_index=False, do_render=False)
    columns = client.get_ohlc_columns()
    macd_p = MACDpreProcess(short_window=12, long_window=26, signal_window=9, target_column=ohlc_columns[3])
    renko_p = RenkoProcess(window=60, date_column=columns["Time"], ohlc_column=ohlc_columns)
    rtp_p = RangeTrendProcess(slope_window=3)
    bband_process = BBANDpreProcess(target_column=columns["Close"], alpha=2)
    st1 = ts.storategies.MACDRenkoRangeSLByBB(client, renko_p, macd_p, bband_process, rtp_p, slope_window = 5, interval_mins = 0, data_length=70, logger=logger)
    manager = ts.ParallelStorategyManager([st1], minutes=60*3, logger=logger)
    manager.start_storategies()    

def MACDRenkoMT5(frame, short_window, long_window, signal_window, renko_window, slope_window):
    client = MT5Client(id=100000000, password="", server="", frame=frame, auto_step_index=True, simulation=True)
    columns = client.get_ohlc_columns()
    data_length = max([short_window, long_window, signal_window, renko_window, slope_window])
    macd_p = MACDpreProcess(short_window=short_window, long_window=long_window, signal_window=signal_window, target_column=columns["Close"])
    renko_p = RenkoProcess(window=renko_window, date_column=columns["Time"], ohlc_column=[columns["Open"], columns["High"], columns["Low"], columns["Close"]])
    st1 = ts.storategies.MACDRenko(client, renko_p, macd_p, slope_window = slope_window, interval_mins = 0, data_length=10, logger=logger)
    manager = ts.ParallelStorategyManager([st1], minutes=10, logger=logger)
    manager.start_storategies()
    
if __name__ == '__main__':
    #MACDRenkoMT5(5, 24, 52, 18, 60, 3)
    #MACDRenkoMT5(5, 8, 16, 6, 60, 3)
    #MACDRenkoMT5(30, 12, 26, 9, 60, 9)
    #MACDRenkoMT5(60, 12, 26, 9, 60, 9)
    MACDRenkoRangeCSV()
    #MACDRenkoRangeSLCSV()