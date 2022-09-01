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
log_path = f'./{log_file_base_name}_mrenko_bb_{datetime.datetime.utcnow().strftime("%Y%m%d%H%M")}.logs'
logger_config["handlers"]["fileHandler"]["filename"] = log_path
config.dictConfig(logger_config)
logger = getLogger("trade_storategy.back_test")

#file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../stocknet/finance_client/finance_client/data_source/csv/USDJPY_forex_min30.csv'))
#date_column = "Time"
file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../stocknet/finance_client/finance_client/data_source/mt5/OANDA-Japan MT5 Live/mt5_USDJPY_min5.csv'))
date_column = "time"
ohlc_column = ["high", "open", "low", "close"]
#file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../stocknet/finance_client/finance_client/data_source/csv/bitcoin_5_2017T0710-2021T103022_5_30.csv'))
#date_column = "Timestamp"
#ohlc_column = ["High", "Open", "Low", "Close"]

def MACDRenkoTPByBBCSV():
    client = CSVClient(file=file_path, frame=5, auto_index=True, start_index=0, logger=logger, columns=ohlc_column, date_column=date_column, slip_type="percentage")
    columns = client.get_ohlc_columns()
    macd_p = MACDpreProcess(short_window=8, long_window=18, signal_window=6, target_column=columns["Close"])
    renko_p = RenkoProcess(window=60, date_column=columns["Time"], ohlc_column=[columns["Open"], columns["High"], columns["Low"], columns["Close"]])
    bb_p = BBANDpreProcess(window=14, alpha=3, target_column=columns["Close"])
    st1 = ts.storategies.MACDRenkoSLByBB(financre_client=client, renko_process=renko_p, macd_process=macd_p, bolinger_process=bb_p, slope_window = 12, interval_mins = 0, use_tp=False, continuous=True, data_length=120, logger=logger)
    manager = ts.ParallelStorategyManager([st1], minutes=60, logger=logger)
    manager.start_storategies()

if __name__ == '__main__':
    #MACDRenkoByBBMT5()
    #MACDRenkoByBBCSV()
    MACDRenkoTPByBBCSV()
    