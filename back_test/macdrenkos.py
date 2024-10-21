import os, json, sys, datetime
from time import sleep

module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(module_path)
import trade_strategy as ts
from finance_client.csv.client import CSVClient
from finance_client.fprocess.fprocess.idcprocess import *

from logging import getLogger, config

try:
    with open(os.path.join(module_path, "trade_strategy/settings.json"), "r") as f:
        settings = json.load(f)
except Exception as e:
    print(f"fail to load settings file: {e}")
    raise e
logger_config = settings["log"]
log_file_base_name = logger_config["handlers"]["fileHandler"]["filename"]
log_path = f'./{log_file_base_name}_mrenko_{datetime.datetime.now(datetime.UTC).strftime("%Y%m%d%H")}.log'
logger_config["handlers"]["fileHandler"]["filename"] = log_path
config.dictConfig(logger_config)
logger = getLogger("trade_strategy.back_test")

nikkei_codes = [
    "1333.T",
    "1332.T",
    "1605.T",
    "1963.T",
    "1812.T",
    "1801.T",
    "1928.T",
    "1802.T",
    "1925.T",
    "1808.T",
    "1803.T",
    "1721.T",
    "2503.T",
    "2502.T",
    "2269.T",
    "2501.T",
    "2914.T",
    "2531.T",
    "2871.T",
    "2002.T",
    "2802.T",
    "2282.T",
    "2801.T",
    "3401.T",
    "3101.T",
    "3103.T",
    "3402.T",
    "3863.T",
    "3861.T",
    "4004.T",
    "4183.T",
    "4631.T",
    "4043.T",
    "4021.T",
    "4061.T",
    "3405.T",
    "4208.T",
    "6988.T",
    "3407.T",
    "4005.T",
    "4188.T",
    "4042.T",
    "4901.T",
    "4911.T",
    "4063.T",
    "4452.T",
    "4151.T",
    "4506.T",
    "4503.T",
    "4502.T",
    "4519.T",
    "4578.T",
    "4507.T",
    "4523.T",
    "4568.T",
    "5019.T",
    "5020.T",
    "5101.T",
    "5108.T",
    "5202.T",
    "5301.T",
    "5214.T",
    "5333.T",
    "5233.T",
    "5201.T",
    "5232.T",
    "5332.T",
    "5406.T",
    "5411.T",
    "5401.T",
    "5541.T",
    "5703.T",
    "3436.T",
    "5803.T",
    "5711.T",
    "5713.T",
    "5802.T",
    "5706.T",
    "5801.T",
    "5707.T",
    "5714.T",
    "5631.T",
    "7004.T",
    "6302.T",
    "6471.T",
    "6113.T",
    "6326.T",
    "6473.T",
    "6301.T",
    "6103.T",
    "6361.T",
    "7013.T",
    "6305.T",
    "7011.T",
    "6367.T",
    "6703.T",
    "6753.T",
    "6841.T",
    "6752.T",
    "6674.T",
    "6952.T",
    "6770.T",
    "6503.T",
    "6479.T",
    "7752.T",
    "6954.T",
    "6506.T",
    "6701.T",
    "6724.T",
    "7751.T",
    "6857.T",
    "7735.T",
    "6976.T",
    "6504.T",
    "6981.T",
    "6645.T",
    "6762.T",
    "6902.T",
    "6758.T",
    "6971.T",
    "6702.T",
    "6501.T",
    "8035.T",
    "6861.T",
    "7003.T",
    "7012.T",
    "7201.T",
    "7211.T",
    "7205.T",
    "7261.T",
    "7202.T",
    "7203.T",
    "7272.T",
    "7270.T",
    "7267.T",
    "7269.T",
    "7762.T",
    "7731.T",
    "4902.T",
    "7733.T",
    "4543.T",
    "7912.T",
    "7911.T",
    "7951.T",
    "7832.T",
    "2768.T",
    "8002.T",
    "8053.T",
    "8058.T",
    "8001.T",
    "8031.T",
    "8015.T",
    "9983.T",
    "3086.T",
    "8233.T",
    "8267.T",
    "3099.T",
    "8252.T",
    "3382.T",
    "8411.T",
    "8306.T",
    "7186.T",
    "8331.T",
    "8308.T",  #'8355.T',
    "8316.T",
    "8304.T",
    "8309.T",
    "8354.T",
    "8604.T",
    "8628.T",
    "8601.T",
    "8766.T",
    "8750.T",
    "8795.T",
    "8725.T",
    "8630.T",
    "8253.T",
    "8591.T",
    "8697.T",
    "8802.T",
    "3289.T",
    "8804.T",
    "8801.T",
    "8830.T",
    "9005.T",
    "9001.T",
    "9007.T",
    "9009.T",
    "9021.T",
    "9020.T",
    "9008.T",
    "9022.T",
    "9147.T",
    "9064.T",
    "9107.T",
    "9101.T",
    "9104.T",
    "9202.T",
    "9301.T",
    "9434.T",
    "9613.T",
    "9432.T",
    "9984.T",
    "9433.T",
    "9501.T",
    "9502.T",
    "9503.T",
    "9532.T",
    "9531.T",
    "9766.T",
    "3659.T",
    "4755.T",
    "6178.T",
    "4689.T",
    "4324.T",
    "4751.T",
    "2432.T",
    "9602.T",
    "2413.T",
    "9735.T",
    "6098.T",
    "4704.T",
    "7974.T",
]

base_path = os.path.dirname(__file__)
frame = 60 * 24
date_column = "Datetime"
ohlc_columns = ["Open", "High", "Low", "Adj Close"]
sleep_time = 60 * 60 * 3
base_path = os.path.dirname(__file__)
file_paths = [f"L:/data/yfinance/yfinance_{symbol}_D1.csv" for symbol in nikkei_codes]


def MACDRenkoCSV():
    stgs = []
    """
    for code in nikkei_codes:
        file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), f'../../stocknet/finance_client/finance_client/data_source/yfinance/yfinance_{code}_D1.csv'))
        client = CSVClient(files=file_path, 
                           symbols=[code],
                           auto_step_index=True, frame=frame, start_index=200, logger=logger, columns=ohlc_columns, date_column=date_column)
        macd_p = MACDProcess(short_window=12, long_window=26, signal_window=9, target_column=ohlc_columns[3])
        renko_p = RenkoProcess(window=14, ohlc_column=ohlc_columns)
        st = ts.strategies.MACDRenko(client, renko_p, macd_p, slope_window = 2, interval_mins = 0, data_length=100, threshold=1, logger=logger)
        stgs.append(st)
    """
    # file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), f'../../stocknet/finance_client/finance_client/data_source/yfinance/yfinance_{code}_D1.csv'))
    client = CSVClient(
        symbols=nikkei_codes,
        file_name_generator=lambda symbol: os.path.join(os.path.abspath(os.path.join(base_path, f"L:/data/yfinance/yfinance_{symbol}_D1.csv"))),
        auto_step_index=True,
        frame=frame,
        start_index=200,
        logger=logger,
        columns=ohlc_columns,
        date_column=date_column,
        enable_trade_log=True,
    )
    macd_p = MACDProcess(short_window=12, long_window=26, signal_window=9, target_column=ohlc_columns[3])
    renko_p = RenkoProcess(window=14, ohlc_column=ohlc_columns)
    st = ts.strategies.MACDRenko(client, renko_p, macd_p, slope_window=2, interval_mins=0, data_length=100, threshold=1, logger=logger)
    print("all strategies are initialized.")
    manager = ts.ParallelStrategyManager([st], minutes=sleep_time / 60, logger=logger)
    manager.start_strategies(False)
    while manager.done is False:
        try:
            sleep(sleep_time)
            manager.done = True
            manager.summary()
        except KeyboardInterrupt:
            manager.done = True
            manager.summary()
            break


if __name__ == "__main__":
    MACDRenkoCSV()
