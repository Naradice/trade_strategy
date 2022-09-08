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
log_path = f'./{log_file_base_name}_range_{datetime.datetime.utcnow().strftime("%Y%m%d%H")}.logs'
logger_config["handlers"]["fileHandler"]["filename"] = log_path
config.dictConfig(logger_config)
logger = getLogger("trade_storategy.back_test")

file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../stocknet/finance_client/finance_client/data_source/mt5/OANDA-Japan MT5 Live/mt5_USDJPY_min30.csv'))
date_column = "time"
ohlc_columns = ["open", "high", "low", "close"]

def RangeTrendCSV():
    client = CSVClient(file=file_path, auto_step_index=True, start_index=0, logger=logger, auto_refresh_index=False, columns=ohlc_columns,date_column=date_column, slip_type="percentage", do_render=False)
    rtp_p = RangeTrendProcess(slope_window=3)
    st1 = ts.storategies.RangeTrade(client, range_process=rtp_p, data_length=30, interval_mins=0, alpha=2, slope_ratio=0.1, logger=logger)
    manager = ts.ParallelStorategyManager([st1], minutes=10, logger=logger)
    manager.start_storategies()

def RangeTrendMT5Simulation(frame):
    client = MT5Client(id=100000000, password="", server="", frame=frame, simulation=True)
    columns = client.get_ohlc_columns()
    rtp_p = RangeTrendProcess()
    st1 = ts.storategies.RangeTrade(client, range_process=rtp_p, data_length=30,interval_mins=-1, logger=logger)
    manager = ts.ParallelStorategyManager([st1], minutes=1, logger=logger)
    manager.start_storategies()
    
if __name__ == '__main__':
    RangeTrendCSV()