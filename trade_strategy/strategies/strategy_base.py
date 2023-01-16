import finance_client as fc
from ..signal import Signal
import pandas as pd
from logging import getLogger, config
import json, os
from trade_strategy.signal import Signal, Trend

class StrategyClient:

    key = "base"
    client: fc.Client = None
    
    def __init__(self, financre_client: fc.Client, idc_processes=[], interval_mins:int=-1, amount=1, data_length:int = 100, save_signal_info=False, logger=None) -> None:
        if logger == None:
            try:
                with open(os.path.abspath(os.path.join(os.path.dirname(__file__), '../settings.json')), 'r') as f:
                        settings = json.load(f)
            except Exception as e:
                self.logger.error(f"fail to load settings file on strategy: {e}")
                raise e
    
            logger_config = settings["log"]
            
            try:
                config.dictConfig(logger_config)
            except Exception as e:
                print(f"fail to set configure file on strategy: {e}")
                raise e

            logger_name = "trade_strategy.strategy"
            self.logger = getLogger(logger_name)
        else:
            self.logger = logger
        self.__idc_processes = idc_processes
        self.save_signal_info = save_signal_info
        self.amount = amount
        self.client = financre_client
        self.data_length = data_length
        if interval_mins < 0:
            self.interval_mins = self.client.frame
        else:
            self.interval_mins = interval_mins
        self.trend = {} #0 don't have, 1 have long_position, -1 short_position
        
    def add_indicaters(self, idc_processes:list):
        for process in idc_processes:
            if process not in self.__idc_processes:
                self.__idc_processes.append(process)
            else:
                self.logger.info(f"{process.kinds} is already added")
                
    def save_signal(self, signal, data):
        #time, signal info, data
        pass
    
    def update_trend(self, signal:Signal):
        if signal is not None:
            self.trend[signal.symbol] = signal.trend
    
    def get_signal(self, df, long_short: int = None, symbols=[]) -> Signal:
        print("please overwrite this method on an actual client.")
        return None
    
    def run(self, symbols:str or list, long_short = None) -> Signal:
        """ run this strategy

        Args:
            long_short (int, optional): represents the trend. When manually or other strategy buy/sell, you can pass 1/-1 to this strategy. Defaults to None.

        Returns:
            Signal: Signal of this strategy
        """
        try:
            df = self.client.get_ohlc(self.data_length, symbols, idc_processes=self.__idc_processes)
        except Exception as e:
            self.logger.error(f"error occured when client gets ohlc data: {e}")
            return []
        signals = []
        if type(symbols) is str:
            symbols = [symbols]
        if len(symbols) == 1:
            get_dataframe = lambda df, key: df
        else:
            get_dataframe = lambda df, key: df[key]
            
        for symbol in symbols:
            if long_short is None:
                if symbol in self.trend:
                    position = self.trend[symbol].id
                else:
                    position = 0
            else:
                position = long_short
            
            ohlc_df = get_dataframe(df, symbol)
            if ohlc_df.iloc[-1].isnull().any() == False:
                signal = self.get_signal(ohlc_df, position, symbol)
                if signal is not None:
                    signal.amount = self.amount
                    signal.symbol = symbol
                    self.update_trend(signal)
                    signals.append(signal)
                    if self.save_signal_info:
                        self.save_signal(signal, ohlc_df)
        
        return signals