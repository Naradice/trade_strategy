import finance_client as fc
import trade_storategy as ts
import pandas as pd
from logging import getLogger, config
import json, os

class Storategy:

    key = "base"
    client: fc.Client = None
    
    def __init__(self, financre_client: fc.Client, interval_mins:int=-1, amount=1, data_length:int = 100, save_signal_info=False, logger=None) -> None:
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
        
        self.save_signal_info = save_signal_info
        self.amount = amount
        self.client = financre_client
        self.data_length = data_length
        if interval_mins < 0:
            self.interval_mins = self.client.frame
        else:
            self.interval_mins = interval_mins
        self.trend = 0#0 don't have, 1 have long_position, -1 short_position
             
    
    def save_signal(self, signal, data):
        #time, signal info, data
        pass
    
    def get_signal(self, df:pd.DataFrame, long_short: int = None):
        self.logger.debug("run base storategy for testing.")
        return None
    
    def run(self, long_short = None) -> ts.Signal:
        """ run this storategy

        Args:
            long_short (int, optional): represents the trend. When manually or other storategy buy/sell, you can pass 1/-1 to this storategy. Defaults to None.

        Returns:
            ts.Signal: Signal of this strategy
        """
        df = self.client.get_rate_with_indicaters(self.data_length)
        signal = self.get_signal(df, long_short)
        if self.save_signal_info:
            self.save_signal(signal, df)
        
        return signal