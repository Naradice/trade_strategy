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
log_path = f'./{log_file_base_name}_range_{datetime.datetime.utcnow().strftime("%Y%m%d%H%M")}.logs'
logger_config["handlers"]["fileHandler"]["filename"] = log_path
config.dictConfig(logger_config)
logger = getLogger("trade_storategy.back_test")

file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../stocknet/finance_client/finance_client/data_source/csv/USDJPY_forex_min30.csv'))
date_column = "Time"

def RangeTrendCSV():
    client = CSVClient(file=file_path, auto_index=True, start_index=0, logger=logger, date_column=date_column, slip_type="percentage", do_render=True)
    rtp_p = RangeTrendProcess()
    st1 = ts.storategies.RangeTrade(client, range_process=rtp_p, data_length=30, interval_mins=0, alpha=2, logger=logger)
    manager = ts.ParallelStorategyManager([st1], minutes=60, logger=logger)
    manager.start_storategies()

def RangeTrendMT5(frame):
    client = MT5Client(id=100000000, password="", server="", frame=frame, auto_index=True, simulation=True)
    columns = client.get_ohlc_columns()
    rtp_p = RangeTrendProcess()
    st1 = ts.storategies.RangeTrade(client, range_process=rtp_p, data_length=30,interval_mins=0, logger=logger)
    manager = ts.ParallelStorategyManager([st1], minutes=1, logger=logger)
    manager.start_storategies()
    
if __name__ == '__main__':
    RangeTrendCSV()