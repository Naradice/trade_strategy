import os, json, sys, datetime

import dotenv

module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(module_path)
import trade_strategy as ts
from finance_client.csv.client import CSVClient
from finance_client.config import AccountRiskConfig
from finance_client.risk_manager.risk_options import ATRRisk
from finance_client import db
from finance_client.fprocess.fprocess.idcprocess import *
from finance_client.fprocess import fprocess

from logging import getLogger, config

try:
    with open(os.path.join(module_path, "trade_strategy/settings.json"), "r") as f:
        settings = json.load(f)
except Exception as e:
    print(f"fail to load settings file: {e}")
    raise e

dotenv.load_dotenv()
logger_config = settings["log"]
log_file_base_name = logger_config["handlers"]["fileHandler"]["filename"]
log_path = f'./{log_file_base_name}_mrenko_{datetime.datetime.now().strftime("%Y%m%d")}.log'
logger_config["handlers"]["fileHandler"]["filename"] = log_path
config.dictConfig(logger_config)
logger = getLogger("trade_strategy.back_test")
data_folder = os.environ["ts_data_folder"]

file_path = os.path.abspath("L:/data/mt5/OANDA-Japan MT5 Live/mt5_USDJPY_h1.csv")
frame = 60

date_column = "time"
ohlc_columns = ["open", "high", "low", "close"]

MINUTES_TO_RUN = 10


def _make_storage(sqlite_path: str, provider: str, user: str):
    """Return a position storage object.  Uses PostgreSQL when PostgreServer env var is set, otherwise SQLite."""
    pg_host = os.environ.get("PostgreServer")
    if pg_host:
        return db.PositionPostgresStorage(
            provider=provider,
            username=user,
            host=pg_host,
            port=int(os.environ.get("PostgrePort", "5432")),
            database=os.environ.get("PostgreDatabase", "postgres"),
            user=os.environ.get("PostgreUsername", "postgres"),
            password=os.environ.get("PostgrePassword", ""),
        )
    if os.path.exists(sqlite_path):
        os.remove(sqlite_path)
    return db.PositionSQLiteStorage(sqlite_path, provider, user)


def MACDRenko(user, provider="csv", slope=5, threshold=2, atr_window=None, brick_size=None, range_function=None, trailing_stop=None,
              account_risk_config=None, risk_option=None):
    additionals = []
    if range_function is not None:
        additionals.append("range")
    if trailing_stop is not None:
        additionals.append("tstop")

    storage = _make_storage("./back_test.db", provider, user)
    client = CSVClient(
        files=file_path,
        auto_step_index=True,
        frame=frame,
        start_index=100,
        columns=ohlc_columns,
        date_column=date_column,
        slip_type="percent",
        storage=storage,
        account_risk_config=account_risk_config,
        risk_option=risk_option
    )
    macd_p = MACDProcess(short_window=12, long_window=26, signal_window=9, target_column=ohlc_columns[3])
    if brick_size is not None:
        renko_p = RenkoProcess(brick_size=brick_size, ohlc_column=ohlc_columns)
    else:
        renko_p = RenkoProcess(window=atr_window, ohlc_column=ohlc_columns)
    st1 = ts.strategies.MACDRenko(client, renko_p, macd_p, slope_window=slope,volume=1,
                                  interval_mins=0, data_length=100, logger=logger, threshold=threshold,
                                  range_function=range_function, trailing_stop=trailing_stop)
    manager = ts.ParallelStrategyManager([st1], minutes=MINUTES_TO_RUN, logger=logger, result_csv_path="./macd_renko_result.csv")
    manager.start_strategies()


def MACDRenkoByBBCSV(slope=5, window=20, provider="csv", user="back_test"):
    ldb = db.LogCSVStorage(provider, user, f"./back_test_USDJPY_{frame}.csv")
    storage = _make_storage("./back_test.db", provider, user)
    client = CSVClient(
        files=file_path,
        auto_step_index=True,
        frame=frame,
        start_index=250,
        columns=ohlc_columns,
        date_column=date_column,
        slip_type="percent",
        storage=storage,
    )
    columns = client.get_ohlc_columns()

    bband_process = BBANDProcess(target_column=columns["Close"], window=window)
    macd_p = MACDProcess(short_window=12, long_window=26, signal_window=9, target_column=ohlc_columns[3])
    renko_p = RenkoProcess(window=60, ohlc_column=ohlc_columns)
    # BBAN std require 200 for data length
    st1 = ts.strategies.MACDRenkoSLByBB(client, renko_p, macd_p, slope_window=slope, bolinger_process=bband_process,
                                         interval_mins=0, data_length=250, logger=logger)
    manager = ts.ParallelStrategyManager([st1], minutes=MINUTES_TO_RUN, logger=logger)
    manager.start_strategies()

def MACDRenkoRangeCSV(slope=5):
    provider = "csv"
    user = "back_test"
    ldb = db.LogCSVStorage(provider, user, f"./back_test_USDJPY_{frame}.csv")
    storage = _make_storage("./back_test.db", provider, user)
    client = CSVClient(
        files=file_path,
        auto_step_index=True,
        frame=frame,
        start_index=150,
        columns=ohlc_columns,
        date_column=date_column,
        slip_type="percent",
        do_render=False,
        storage=storage,
    )
    macd_p = MACDProcess(short_window=12, long_window=26, signal_window=9, target_column=ohlc_columns[3])
    renko_p = RenkoProcess(window=60, ohlc_column=ohlc_columns)
    rtp_p = RangeTrendProcess(slope_window=3)
    st1 = ts.strategies.MACDRenkoRange(client, renko_p, macd_p, rtp_p, slope_window=slope, interval_mins=0, data_length=120, logger=logger)
    manager = ts.ParallelStrategyManager([st1], minutes=MINUTES_TO_RUN, logger=logger)
    manager.start_strategies()


def MACDRenkoRangeSLCSV(slope_window=5, use_tp=True):
    provider = "csv"
    user = "back_test"
    ldb = db.LogCSVStorage(provider, user, f"./back_test_USDJPY_{frame}.csv")
    storage = _make_storage("./back_test.db", provider, user)
    client = CSVClient(
        files=file_path,
        auto_step_index=True,
        frame=frame,
        start_index=150,
        columns=ohlc_columns,
        date_column=date_column,
        slip_type="percent",
        do_render=False,
        storage=storage,
    )
    columns = client.get_ohlc_columns()
    macd_p = MACDProcess(short_window=12, long_window=26, signal_window=9, target_column=ohlc_columns[3])
    renko_p = RenkoProcess(window=60, ohlc_column=ohlc_columns)
    rtp_p = RangeTrendProcess(slope_window=3)
    bband_process = BBANDProcess(target_column=columns["Close"], alpha=2)
    st1 = ts.strategies.MACDRenkoRangeSLByBB(
        client,
        renko_p,
        macd_p,
        bband_process,
        rtp_p,
        slope_window=slope_window,
        interval_mins=0,
        data_length=120,
        use_tp=use_tp,
        logger=logger,
        alpha=4,
        bolinger_threshold=2,
    )
    
    manager = ts.ParallelStrategyManager([st1], minutes=MINUTES_TO_RUN, logger=logger)
    manager.start_strategies()


if __name__ == "__main__":
    user = "mscdrenko_atrrisk_range_tstop3"
    account_risk_config = AccountRiskConfig(
        base_currency="JPY",
        max_single_trade_percent=None,
        max_total_risk_percent=None,
        daily_max_loss_percent=None,
        allow_aggressive_mode=False,
        aggressive_multiplier=None,
        enforce_volume_reduction=True,
        atr_ratio_min_stop_loss=None,
    )
    risk_option = ATRRisk(percent=1.0, atr_window=14, atr_multiplier=6.0, ohlc_columns=ohlc_columns, rr_ratio=2.0)
    # risk_option = None
    # range_function = lambda df: fprocess.regime.range_detection_by_atr(df, mean_window=100, atr_window=14, range_threshold=0.6, ohlc_columns=ohlc_columns)
    range_function = lambda df: fprocess.regime.range_detection_by_bollinger(df,std_window=200, window=20, std_threshold=0.6, ohlc_columns=ohlc_columns)
    # range_function = None
    trailing_stop = ts.trailingstop.TrailingStopByATR(atr_window=7, atr_multiplier=3.0, ohlc_columns=ohlc_columns, clip_with_price=False)
    # trailing_stop = None
    MACDRenko(
        user, 0, threshold=2, atr_window=7, range_function=range_function, trailing_stop=trailing_stop, 
        account_risk_config=account_risk_config, risk_option=risk_option
    )
    # MACDRenkoByBBCSV(slope=5, window=14)
    # MACDRenkoRangeCSV(slope=2)
    # MACDRenkoRangeSLCSV(slope_window=2, use_tp=False)
