import finance_client as fc
import trade_storategy as ts
import pandas as pd
from logging import getLogger, config
import json, os
from trade_storategy.signal import Signal, Trend

class StorategyClient:

    key = "base"
    client: fc.Client = None
    
    def __init__(self, financre_client: fc.Client, idc_processes=[], interval_mins:int=-1, amount=1, data_length:int = 100, save_signal_info=False, logger=None) -> None:
        if logger == None:
            try:
                with open(os.path.abspath(os.path.join(os.path.dirname(__file__), '../settings.json')), 'r') as f:
                        settings = json.load(f)
            except Exception as e:
                self.logger.error(f"fail to load settings file on storategy: {e}")
                raise e
    
            logger_config = settings["log"]
            
            try:
                config.dictConfig(logger_config)
            except Exception as e:
                print(f"fail to set configure file on storategy: {e}")
                raise e

            logger_name = "trade_storategy.storategy"
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
        self.trend = Trend()#0 don't have, 1 have long_position, -1 short_position
        
    def add_indicaters(self, idc_processes:list):
        for process in idc_processes:
            if process not in self.__idc_processes:
                self.__idc_processes.append(process)
            else:
                self.logger.info(f"{process.kinds} is already added")
                
    def save_signal(self, signal, data):
        #time, signal info, data
        pass
    
    def update_trend(self, signal:ts.Signal):
        if signal is not None:
            self.trend = signal.trend
    
    def get_signal(self, df, long_short: int = None) -> Signal:
        print("please overwrite this method on an actual client.")
        return None
    
    def run(self, long_short = None) -> ts.Signal:
        """ run this storategy

        Args:
            long_short (int, optional): represents the trend. When manually or other storategy buy/sell, you can pass 1/-1 to this storategy. Defaults to None.

        Returns:
            ts.Signal: Signal of this strategy
        """
        if long_short is None:
            position = self.trend.id
        else:
            position = long_short
        df = self.client.get_ohlc(self.data_length, idc_processes=self.__idc_processes)
        signal = self.get_signal(df, position)
        if signal is not None:
            signal.amount = self.amount
            self.update_trend(signal)
        if self.save_signal_info:
            self.save_signal(signal, df)
        
        return signal