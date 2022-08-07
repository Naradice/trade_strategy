import modules.finance_client as fc
import trade_storategy as ts
from logging import getLogger, config
import json, os
from trade_storategy.signal import *

class Storategy:

    key = "base"
    client: fc.Client = None
    
    def __init__(self, financre_client: fc.Client, interval_mins:int=-1, amount=1, data_length:int = 100, logger=None) -> None:
        if logger == None:
            try:
                settings_file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../settings.json'))
                with open(settings_file_path, 'r') as f:
                        settings = json.load(f)
            except Exception as e:
                print(f"fail to load settings file on storategy: {e}")
                raise e
    
            logger_config = settings["log"]
            logger_name = "trade_storategy.storategy"
            self.logger = getLogger(logger_name)
            
            try:
                config.dictConfig(logger_config)
            except Exception as e:
                print(f"fail to set configure file on storategy: {e}")
                raise e
        else:
            self.logger = logger
        
        self.amount = amount
        self.client = financre_client
        self.data_length = data_length
        if interval_mins < 0:
            self.interval_mins = self.client.frame
        else:
            self.interval_mins = interval_mins
        self.trend = 0#0 don't have, 1 long_position, -1 short_position

    def create_signal(self, is_buy, is_close, price) -> Signal:
        if is_buy:
            if is_close:
                return CloseBuySignal(self.key, price)
            else:
                return BuySignal(self.key, price)
        else:
            if is_close:
                return CloseSellSignal(self.key, price)
            else:
                return SellSignal(self.key, price)
             
        
    def run(self, long_short = None) -> Signal:
        """ run this storategy

        Args:
            long_short (int, optional): represents the trend. When manually or other storategy buy/sell, you can pass 1/-1 to this storategy. Defaults to None.

        Returns:
            ts.Signal: Signal of this strategy
        """
        self.logger.debug("run base storategy for testing.")
        return Signal(std_name="base")