from trade_storategy.storategies.strategy_base import Storategy
from trade_storategy.signal import *
import finance_client as fc
import json

class EMACross(Storategy):
    pass

class WMACross(Storategy):
    pass

class MACDCross(Storategy):
    
    key = "macd_cross"
    
    def __get_macd_trend(self):
        #1:long, -1:short
        data = self.client.get_rate_with_indicaters(self.data_length)
        if type(data) != type(None) and self.signal_column_name in data and len(data[self.signal_column_name]) == self.data_length:
                signal = data[self.signal_column_name].iloc[-1]
                macd = data[self.macd_column_name].iloc[-1]
                self.logger.debug(f"macd: {macd}, signal:{signal}")
                if macd >= signal:
                    return 1, data[self.close_column_name].iloc[-1]
                else:
                    return -1, data[self.close_column_name].iloc[-1]
        return 0, None
    
    def __init__(self, finance_client: fc.Client, macd_process = None, interval_mins: int = 30, data_length=100, logger=None) -> None:
        """ When MACD cross up, return buy signal
            When MACD cross down, return sell signal

        Args:
            finance_client (fc.Client): data client
            interval_mins (int, optional): interval mins to get data. Defaults to -1.
            data_length (int, optional): length to caliculate the MACD. Defaults to 100.
            macd_process (Process, optional): You can specify specific parameter of MACD Process. Defaults to None.
        """
        super().__init__(finance_client, interval_mins, data_length, logger)
        if macd_process == None:
            macd = fc.utils.MACDpreProcess()
        else:
            if macd.kinds == "MACD":
                macd = macd_process
            else:
                raise Exception("MACDCross accept only MACDProcess")
        if finance_client.have_process(macd) == False:
            finance_client.add_indicater(macd)
            
        self.macd_column_name = macd.columns["MACD"]
        self.signal_column_name = macd.columns["Signal"]
        column_dict = self.client.get_ohlc_columns()
        if type(column_dict) == dict:
            self.close_column_name = column_dict["Close"]
        else:
            self.close_column_name = "Close"
        self.current_trend, _ = self.__get_macd_trend()
        self.logger.info(f"initialized macd storategy: trend is {self.current_trend}")
            
    def run(self, long_short = None):
        tick_trend, price = self.__get_macd_trend()
        signal = None
        if tick_trend != 0:
            if long_short != None:
                long_short = self.trend#0 by default
            if self.current_trend == 1 and tick_trend == -1:
                self.current_trend = tick_trend
                if long_short == 1:
                    self.logger.info("CloseSell signal raised.")
                    signal = CloseSellSignal(self.key, amount=self.amount, price=price)
                else:
                    self.logger.info("Sell signal raised.")
                    signal = SellSignal(self.key, price=price)
                self.trend = -1
            elif self.current_trend == -1 and tick_trend == 1:
                self.current_trend = tick_trend
                if long_short == -1:
                    self.logger.info("CloseBuy signal raised.")
                    signal = CloseBuySignal(self.key, amount=self.amount, price=price)
                else:
                    self.logger.info("Buy signal raised.")
                    signal = BuySignal(self.key, amount=self.amount, price=price)
            return signal
        
class MACDRenko(Storategy):
    
    def __init__(self, finance_client: fc.Client, renko_process: fc.utils.RenkoProcess, macd_process: fc.utils.MACDpreProcess, slope_window = 5, continuous=False, amount=1, interval_mins: int = -1, data_length=250, logger=None) -> None:
        super().__init__(finance_client, interval_mins, amount, data_length, logger)
        
        if renko_process.kinds != "Renko":
            if finance_client.have_process(fc.utils.RenkoProcess()) is False:
                raise Exception("renko_process accept only RenkoProcess")
            
        if macd_process.kinds != "MACD":
            if finance_client.have_process(fc.utils.MACDpreProcess()) is False:
                raise Exception("macd_process accept only MACDProcess")
        self.__continuous = continuous
        self.macd_column_column = macd_process.columns["MACD"]
        self.macd_signal_column = macd_process.columns["Signal"]
        self.renko_bnum_column = renko_process.columns["NUM"]
        column_dict = self.client.get_ohlc_columns()
        if type(column_dict) == dict:
            self.close_column_name = column_dict["Close"]
        else:
            self.close_column_name = "Close"
        
        macd_slope = fc.utils.SlopeProcess(key="m", target_column=self.macd_column_column, window=slope_window)
        signal_slope = fc.utils.SlopeProcess(key="s", target_column=self.macd_signal_column, window=slope_window)
        self.slope_macd_column = macd_slope.columns["Slope"]
        self.slope_signal_column = signal_slope.columns["Slope"]
        
        finance_client.add_indicaters([renko_process, macd_process, macd_slope, signal_slope])

            
    def run(self, long_short: int = None, data_df = None):
        if data_df is None:
            df = self.client.get_rate_with_indicaters(self.data_length)
        else:
            df = data_df
        if long_short is None:
            long_short = self.trend#0 by default
        signal = None
        if len(df) > 0:
            last_df = df.iloc[-1]
            self.logger.debug(f"{last_df[self.renko_bnum_column]}, {last_df[self.macd_column_column]}, {last_df[self.macd_signal_column]}, {last_df[self.slope_macd_column]}, {last_df[self.slope_signal_column]}")
            if long_short == 0:
                if last_df[self.renko_bnum_column]>=2 and last_df[self.macd_column_column]>last_df[self.macd_signal_column] and last_df[self.slope_macd_column]>last_df[self.slope_signal_column]:
                    signal = BuySignal(std_name=self.key, amount=self.amount, price=df[self.close_column_name].iloc[-1])
                    self.trend = 1
                elif last_df[self.renko_bnum_column]<=-2 and last_df[self.macd_column_column]<last_df[self.macd_signal_column] and last_df[self.slope_macd_column]<last_df[self.slope_signal_column]:
                    signal = SellSignal(std_name=self.key, amount=self.amount, price=df[self.close_column_name].iloc[-1])
                    self.trend = -1
                        
            elif long_short == 1:
                if last_df[self.renko_bnum_column]<=-2 and last_df[self.macd_column_column]<last_df[self.macd_signal_column] and last_df[self.slope_macd_column]<last_df[self.slope_signal_column]:
                    signal = CloseSellSignal(std_name=self.key, amount=self.amount, price=df[self.close_column_name].iloc[-1])
                    self.trend = -1
                elif last_df[self.macd_column_column]<last_df[self.macd_signal_column] and last_df[self.slope_macd_column]<last_df[self.slope_signal_column]:
                    if self.__continuous:
                        signal = CloseSellSignal(std_name=self.key, amount=self.amount, price=df[self.close_column_name].iloc[-1])
                        self.trend = -1
                    else:
                        signal = CloseSignal(std_name=self.key)
                        self.trend = 0
                    
            elif long_short == -1:
                if last_df[self.renko_bnum_column]>=2 and last_df[self.macd_column_column]>last_df[self.macd_signal_column] and last_df[self.slope_macd_column]>last_df[self.slope_signal_column]:
                    signal = CloseBuySignal(std_name=self.key,  amount=self.amount, price=df[self.close_column_name].iloc[-1])
                    self.trend = 1
                elif last_df[self.macd_column_column]>last_df[self.macd_signal_column] and last_df[self.slope_macd_column]>last_df[self.slope_signal_column]:
                    if self.__continuous:
                        signal = CloseBuySignal(std_name=self.key,  amount=self.amount, price=df[self.close_column_name].iloc[-1])
                        self.trend = 1
                    else:
                        signal = CloseSignal(std_name=self.key)
                        self.trend = 0
        return signal
    
class MACDRenkoSLByBB(MACDRenko):
    
    key = "bmacd_renko"
    
    def __init__(self, finance_client: fc.Client, renko_process: fc.utils.RenkoProcess, macd_process: fc.utils.MACDpreProcess, bolinger_process:fc.utils.BBANDpreProcess, slope_window = 5, amount=1, use_tp= False, continuous=False, interval_mins: int = -1, data_length=250, logger=None) -> None:
        """
        add condition to open a position by Bolinger Band
        
        Args:
            finance_client (fc.Client): Cliet
            renko_process (fc.utils.RenkoProcess): Renko Process of finance_client module
            macd_process (fc.utils.MACDpreProcess): MACD Process of finance_client module
            bolinger_process (fc.utils.BBANDpreProcess): BB Process of finance_client module
            slope_window (int, optional): window to caliculate window of the close. Defaults to 5.
            use_tp (bool, optional): Specify a method to add tp vaelue. If not to be specified, "none". Defaults to BB. ["BB", "none", "Fix Ratio"]
            interval_mins (int, optional): update interval. If -1 is specified, use frame of the client. Defaults to -1.
            data_length (int, optional): Length to caliculate the indicaters. Defaults to 250.
            logger (optional): You can pass your logger. Defaults to None.
        """
        ##check if bolinger_process is an instannce of BBANDpreProcess
        super().__init__(finance_client=finance_client, renko_process=renko_process, macd_process=macd_process, slope_window=slope_window, continuous=continuous, interval_mins=interval_mins, amount=amount, data_length=data_length, logger=logger)
        
        ##initialize required columns
        self.bolinger_columns = bolinger_process.columns
        self.b_option = bolinger_process.option
        self.b_alpha = self.b_option["alpha"]
        ## add BBANDPreProcess
        self.client.add_indicater(bolinger_process)
        self.use_tp = use_tp
        self.column_dict = self.client.get_ohlc_columns()

        
    def run(self, long_short: int = None):
        df = self.client.get_rate_with_indicaters(self.data_length)
        signal = super().run(long_short, df)
        
        if self.use_tp:
            positions = self.client.get_positions()
            if len(positions) > 0:#if any position exists, check values to take profit
                width = df.iloc[-1][self.bolinger_columns["Width"]]
                unit_width = width/self.b_alpha
                order_price = None
                for position in positions:
                    if position.order_type == "ask":
                        bid_value = self.client.get_current_bid()
                        if signal is None:
                            order_price = bid_value#assign to pass the condition
                        else:
                            order_price = signal.order_price
                        upper_value = df.iloc[-1][self.bolinger_columns["UV"]]
                        if df.iloc[-1][self.column_dict["High"]] >= upper_value and bid_value >= upper_value - unit_width and bid_value >= order_price:
                            #signal = update_signal_with_close(signal, continuous_mode="long", std_name=self.key)
                            signal = update_signal_with_close(signal, std_name=self.key)
                            #self.logger.info("signal is updated with close as value is too high")
                        break#bidirectional order is not supported for this storategy
                    elif position.order_type == "bid":
                        #short position exists
                        ask_value = self.client.get_current_ask()
                        if signal is None:
                            order_price = ask_value#assign to pass the condition
                        else:
                            order_price = signal.order_price
                        lower_value = df.iloc[-1][self.bolinger_columns["LV"]]
                        if df.iloc[-1][self.column_dict["Low"]] <= lower_value and ask_value <= lower_value + unit_width and ask_value <= order_price:
                            self.logger.debug(f"org signal is {signal}")
                            signal = update_signal_with_close(signal, std_name=self.key)
                            #signal = update_signal_with_close(signal, continuous_mode="short", std_name=self.key)
                            self.logger.info("signal is updated with close as value is too low")
                            self.logger.debug(signal)
        
        #if signal is raised, check values for stop loss
        if signal is not None:
            #check bolinger band range
            if signal.is_buy is True:
                self.logger.info("buy signal is raised. Start adding a sl")
                lower_value = df.iloc[-1][self.bolinger_columns["LV"]]
                current_rate = self.client.get_current_ask()
                mean_value = df.iloc[-1][self.bolinger_columns["MV"]]
                if current_rate > mean_value:
                    self.logger.info(f"added sl by mean_value: {mean_value}")
                    signal.sl = mean_value
                elif current_rate > lower_value:
                    self.logger.info(f"added sl by lower_value: {lower_value}")
                    signal.sl = lower_value
                else:
                    self.logger.info("don't add the sl as current value is too low")
                    
            elif signal.is_buy is False:#sell case
                self.logger.info("sell signal is raised. Start adding a sl")
                current_rate = self.client.get_current_bid()
                mean_value = df.iloc[-1][self.bolinger_columns["MV"]]
                upper_value = df.iloc[-1][self.bolinger_columns["UV"]]
                if current_rate < mean_value:
                    self.logger.info(f"added sl by mean_value: {mean_value}")
                    signal.sl = mean_value
                elif current_rate < upper_value:
                    self.logger.info(f"added sl by upper_value: {upper_value}")
                    signal.sl = upper_value
                else:
                    self.logger.info("don't add sl as current value is too high")
                    
            elif signal.is_close:
                pass
            
            else:            
                self.logger.error(f"unkown signal type {signal.is_buy}")
                signal = None
                self.trend = 0
                
        return signal

class CCICross(Storategy):
    
    key = "cci_cross"
    
    def __init__(self, finance_client: fc.Client, cci_process = None, interval_mins: int = 30, data_length=100, logger=None) -> None:
        """ Raise Buy/Sell signal when CCI cross up/down 0

        Args:
            finance_client (fc.Client): any finance_client
            cci_process (ProcessBase, optional): you can provide CCIProcess. Defaults to None and CCIProcess with default parameter is used.
            interval_mins (int, optional): interval minutes to run this storategy. Defaults to 30.
            data_length (int, optional): data length to caliculate CCI. Defaults to 100.
            logger (Logger, optional): you can specify your logger. Defaults to None.

        Raises:
            Exception: when other than CCI process is provided.
        """
        super().__init__(finance_client, interval_mins, data_length, logger)
        if cci_process == None:
            cci_process = fc.utils.CCIProcess()
        else:
            if cci_process.kinds != "CCI":
                raise Exception("CCICross accept only CCIProcess")
        if finance_client.have_process(cci_process) == False:
            finance_client.add_indicater(cci_process)
            
        self.cci_column_name = cci_process.columns["CCI"]
        column_dict = self.client.get_ohlc_columns()
        if type(column_dict) == dict:
            self.close_column_name = column_dict["Close"]
        else:
            self.close_column_name = "Close"
        self.logger.info(f"initialized cci storategy")
        df = self.client.get_rate_with_indicaters(self.data_length)
        last_df = df.iloc[-1]
        current_cci = last_df[self.cci_column_name]
        if current_cci > 0:
            self.trend = 1
        else:
            self.trend = -1

            
    def run(self, long_short = None):
        
        df = self.client.get_rate_with_indicaters(self.data_length)
        
        if long_short == None:
            long_short = self.trend#0 by default
        signal = None
        if len(df) > 0:
            last_df = df.iloc[-1]
            current_cci = last_df[self.cci_column_name]
            self.logger.debug(f"{current_cci}")
            if long_short == 0:
                #don't return signal
                if current_cci > 0:
                    self.trend = 1
                else:
                    self.trend = -1
            elif long_short == 1:
                if current_cci < 0:
                    signal = CloseSellSignal(std_name=self.key, price=df[self.close_column_name].iloc[-1])
                    self.trend = -1
            elif long_short == -1:
                if current_cci > 0:
                    signal = CloseBuySignal(std_name=self.key, price=df[self.close_column_name].iloc[-1])
                    self.trend = 1
        return signal
    
class CCIBoader(Storategy):
    
    key = "cci_boader"
    
    def __init__(self, finance_client: fc.Client, cci_process = None, upper=100, lower = -100, interval_mins: int = 30, data_length=100, logger=None) -> None:
        """ Raise Buy/Sell signal when CCI cross up/down uppser/lower

        Args:
            finance_client (fc.Client): any finance_client
            cci_process (ProcessBase, optional): you can provide CCIProcess. Defaults to None and CCIProcess with default parameter is used.
            upper (int, option): upper value to raise Buy Signal. Defaults to 100
            lower (int, option): lower value to raise Sell Signal. Defaults to -100
            interval_mins (int, optional): interval minutes to run this storategy. Defaults to 30.
            data_length (int, optional): data length to caliculate CCI. Defaults to 100.
            logger (Logger, optional): you can specify your logger. Defaults to None.

        Raises:
            Exception: when other than CCI process is provided.
            ValueException: when lower >= upper
        """
        super().__init__(finance_client, interval_mins, data_length, logger)
        if lower >= upper:
            raise ValueError("lower should be lower than upper")
        else:
            self.upper = upper
            self.lower = lower
            
        if cci_process == None:
            cci_process = fc.utils.CCIProcess()
        else:
            if cci_process.kinds != "CCI":
                raise Exception("CCICross accept only CCIProcess")
        if finance_client.have_process(cci_process) == False:
            finance_client.add_indicater(cci_process)
            
        self.cci_column_name = cci_process.columns["CCI"]
        column_dict = self.client.get_ohlc_columns()
        if type(column_dict) == dict:
            self.close_column_name = column_dict["Close"]
        else:
            self.close_column_name = "Close"
        self.logger.info(f"initialized cci storategy")
        df = self.client.get_rate_with_indicaters(self.data_length)
        last_df = df.iloc[-1]
        current_cci = last_df[self.cci_column_name]
        if current_cci >= upper:
            self.trend = 1
        elif current_cci <= lower:
            self.trend = -1
        else:
            self.trend = 0

            
    def run(self, long_short = None):
        
        df = self.client.get_rate_with_indicaters(self.data_length)
        
        if long_short == None:
            long_short = self.trend#0 by default
        signal = None
        if len(df) > 0:
            last_df = df.iloc[-1]
            current_cci = last_df[self.cci_column_name]
            self.logger.debug(f"{current_cci}")
            if long_short != 1:
                if current_cci >= self.upper:
                    if current_cci >= self.upper * 2:
                        self.logger.info(f"Buy signal is not raised as cci is too high {current_cci}")
                    else:
                        self.logger.debug(f"Buy signal is raised as cci over 100: {current_cci}")
                        signal = CloseBuySignal(std_name=self.key, price=df[self.close_column_name].iloc[-1])
                    self.trend = 1
                elif self.lower < current_cci:
                    self.trend = 0
                    if long_short == -1:
                        signal = CloseSignal(std_name=self.key, price=df[self.close_column_name].iloc[-1])
            elif long_short != -1:
                if current_cci <= self.lower:
                    if current_cci <= self.lower * 2:
                        self.logger.info(f"Sell signal is not raised as cci is too low {current_cci}")
                    else:
                        self.logger.debug(f"Buy signal is raised as cci over -100: {current_cci}")
                        signal = CloseSellSignal(std_name=self.key, price=df[self.close_column_name].iloc[-1])
                    self.trend = -1
                elif self.upper > current_cci:
                    self.trend = 0
                    if long_short == 1:
                        signal = CloseSignal(std_name=self.key, price=df[self.close_column_name].iloc[-1])
        return signal
    
class RangeTrade(Storategy):
    
    key = "range"
    
    def __init__(self, finance_client: fc.Client, range_process=None, alpha=1, slope_ratio=0.4, interval_mins: int = -1, amount=1, data_length: int = 100, logger=None) -> None:
        super().__init__(finance_client, interval_mins, amount, data_length, logger)
        ohlc_columns = finance_client.get_ohlc_columns()
        self.close_column = ohlc_columns["Close"]
        self.high_column = ohlc_columns["High"]
        self.low_column = ohlc_columns["Low"]
        if range_process is None:
            range_process = fc.utils.RangeTrendProcess()
        bband_process = fc.utils.BBANDpreProcess(target_column=self.close_column, alpha=alpha)
        if finance_client.have_process(bband_process) is False:
            finance_client.add_indicater(bband_process)
        if finance_client.have_process(range_process) is False:
            finance_client.add_indicater(range_process)
        ##initialize params of range indicater
        temp = finance_client.do_render
        finance_client.do_render = False
        finance_client.get_rate_with_indicaters()
        finance_client.do_render = temp
        self.trend_possibility_column = range_process.columns["trend"]
        self.range_possibility_column = range_process.columns["range"]
        self.Width_column = bband_process.columns["Width"]
        self.UV_column = bband_process.columns["UV"]
        self.LV_column = bband_process.columns["LV"]
        self.MV_column = bband_process.columns["MV"]
        self.alpha = alpha
        self.__tp_threrad = slope_ratio
        
    def run(self):
        df = self.client.get_rate_with_indicaters(self.data_length)
        rp = df[self.range_possibility_column].iloc[-1]
        tp = df[self.trend_possibility_column].iloc[-1]
        signal = None
        if rp < 0.6:
            width = df[self.Width_column].iloc[-1]
            std = width/(self.alpha*2)
                #pending order is not implemented for now...
            if self.trend == 0:
                if tp < - self.__tp_threrad:
                    signal = BuySignal(self.key, self.amount, df[self.close_column].iloc[-1], tp=df[self.close_column].iloc[-1]+std*4, sl=df[self.close_column].iloc[-1]-std*2)
                    self.trend = 1
                elif tp < self.__tp_threrad:#Unbalance
                    pass
                else:
                    signal = SellSignal(self.key, self.amount, df[self.close_column].iloc[-1], sl=df[self.close_column].iloc[-1]+std*2,tp=df[self.close_column].iloc[-1]-std*4)
                    self.trend = -1
            elif self.trend == -1:
                if tp < -self.__tp_threrad:
                    signal = CloseSignal(self.key, df[self.close_column].iloc[-1])
                    self.trend = 0
                elif tp < self.__tp_threrad:
                    signal = CloseSignal(self.key, df[self.close_column].iloc[-1])
                    self.trend = 0
                else:
                    self.logger.debug("wait as we have long position on long trend")
            else:
                if tp < -self.__tp_threrad:
                    self.logger.debug("wait as we have short position on short trend")
                elif tp < self.__tp_threrad:
                    signal = CloseSignal(self.key, df[self.close_column].iloc[-1])
                    self.trend = 0
                else:
                    signal = CloseSignal(self.key, df[self.close_column].iloc[-1])
                    self.trend = 0
        else:
            if self.trend != 0:
                if self.trend == 1 and tp > self.__tp_threrad:
                    pass
                elif self.trend == -1 and tp < -self.__tp_threrad:
                    pass
                else:
                    signal = CloseSignal(self.key, df[self.close_column].iloc[-1])
                    self.trend = 0
                    self.logger.info("Colose signal as range trend end.")

        return signal
         
class MACDRenkoRange(Storategy):
    
    def __init__(self, finance_client: fc.Client, renko_process: fc.utils.RenkoProcess, macd_process: fc.utils.MACDpreProcess, range_process: fc.utils.RangeTrendProcess, slope_window = 5, alpha=2, amount=1, interval_mins: int = -1, data_length=250, logger=None) -> None:
        super().__init__(finance_client, interval_mins, amount, data_length, logger)
        
        if renko_process.kinds != "Renko":
            if finance_client.have_process(fc.utils.RenkoProcess()) is False:
                raise Exception("renko_process accept only RenkoProcess")
            
        if macd_process.kinds != "MACD":
            if finance_client.have_process(fc.utils.MACDpreProcess()) is False:
                raise Exception("macd_process accept only MACDProcess")
        column_dict = self.client.get_ohlc_columns()
        if type(column_dict) == dict:
            self.close_column_name = column_dict["Close"]
        else:
            self.close_column_name = "Close"

        if range_process is None or range_process.kinds != fc.utils.RangeTrendProcess.kinds:
            range_process = fc.utils.RangeTrendProcess()
        bband_process = fc.utils.BBANDpreProcess(target_column=self.close_column_name, alpha=alpha)
        self.alpha = alpha
        if finance_client.have_process(bband_process) is False:
            finance_client.add_indicater(bband_process)
        if finance_client.have_process(range_process) is False:
            finance_client.add_indicater(range_process)
        self.macd_column_column = macd_process.columns["MACD"]
        self.macd_signal_column = macd_process.columns["Signal"]
        self.renko_bnum_column = renko_process.columns["NUM"]
        
        macd_slope = fc.utils.SlopeProcess(key="m", target_column=self.macd_column_column, window=slope_window)
        signal_slope = fc.utils.SlopeProcess(key="s", target_column=self.macd_signal_column, window=slope_window)
        self.slope_macd_column = macd_slope.columns["Slope"]
        self.slope_signal_column = signal_slope.columns["Slope"]
        self.trend_possibility_column = range_process.columns["trend"]
        self.range_possibility_column = range_process.columns["range"]
        self.Width_column = bband_process.columns["Width"]
        finance_client.add_indicaters([renko_process, macd_process, macd_slope, signal_slope])

            
    def run(self, long_short: int = None, data_df = None):
        if data_df is None:
            df = self.client.get_rate_with_indicaters(self.data_length)
        else:
            df = data_df
        if long_short is None:
            long_short = self.trend#0 by default
        signal = None
        if len(df) > 0:
            rp = df[self.range_possibility_column].iloc[-1]
            # width = df[self.Width_column].iloc[-1]
            # std = width/(self.alpha*2)
            last_df = df.iloc[-1]
            self.logger.debug(f"{last_df[self.renko_bnum_column]}, {last_df[self.macd_column_column]}, {last_df[self.macd_signal_column]}, {last_df[self.slope_macd_column]}, {last_df[self.slope_signal_column]}")
            if long_short == 0:
                if last_df[self.renko_bnum_column]>=2 and last_df[self.macd_column_column]>last_df[self.macd_signal_column] and last_df[self.slope_macd_column]>last_df[self.slope_signal_column]:
                    if rp <= 0.65:
                        signal = BuySignal(std_name=self.key, amount=self.amount, price=df[self.close_column_name].iloc[-1])
                        self.trend = 1
                    else:
                        signal = SellSignal(std_name=self.key, amount=self.amount, price=df[self.close_column_name].iloc[-1])
                        self.trend = -1
                elif last_df[self.renko_bnum_column]<=-2 and last_df[self.macd_column_column]<last_df[self.macd_signal_column] and last_df[self.slope_macd_column]<last_df[self.slope_signal_column]:
                    if rp <= 0.65:
                        signal = SellSignal(std_name=self.key, amount=self.amount, price=df[self.close_column_name].iloc[-1])
                        self.trend = -1
                    else:
                        signal = BuySignal(std_name=self.key, amount=self.amount, price=df[self.close_column_name].iloc[-1])
                        self.trend = 1
                        
            elif long_short == 1:
                if last_df[self.renko_bnum_column]<=-2 and last_df[self.macd_column_column]<last_df[self.macd_signal_column] and last_df[self.slope_macd_column]<last_df[self.slope_signal_column]:
                    signal = CloseSellSignal(std_name=self.key, amount=self.amount, price=df[self.close_column_name].iloc[-1])
                    self.trend = -1
                elif last_df[self.macd_column_column]<last_df[self.macd_signal_column] and last_df[self.slope_macd_column]<last_df[self.slope_signal_column]:
                    signal = CloseSignal(std_name=self.key)
                    self.trend = 0
                    
            elif long_short == -1:
                if last_df[self.renko_bnum_column]>=2 and last_df[self.macd_column_column]>last_df[self.macd_signal_column] and last_df[self.slope_macd_column]>last_df[self.slope_signal_column]:
                    signal = CloseBuySignal(std_name=self.key,  amount=self.amount, price=df[self.close_column_name].iloc[-1])
                    self.trend = 1
                elif last_df[self.macd_column_column]>last_df[self.macd_signal_column] and last_df[self.slope_macd_column]>last_df[self.slope_signal_column]:
                    signal = CloseSignal(std_name=self.key)
                    self.trend = 0
        return signal
    
class MACDRenkoRangeSLByBB(MACDRenkoRange):
    
    key = "bmacd_renkor"
    
    
    def __init__(self, finance_client: fc.Client, renko_process: fc.utils.RenkoProcess, macd_process: fc.utils.MACDpreProcess, bolinger_process:fc.utils.BBANDpreProcess, range_process=None, slope_window = 5, amount=1, use_tp= False, interval_mins: int = -1, data_length=250, logger=None) -> None:
        """
        add condition to open a position by Bolinger Band
        
        Args:
            finance_client (fc.Client): Cliet
            renko_process (fc.utils.RenkoProcess): Renko Process of finance_client module
            macd_process (fc.utils.MACDpreProcess): MACD Process of finance_client module
            bolinger_process (fc.utils.BBANDpreProcess): BB Process of finance_client module
            slope_window (int, optional): window to caliculate window of the close. Defaults to 5.
            use_tp (bool, optional): Specify a method to add tp vaelue. If not to be specified, "none". Defaults to BB. ["BB", "none", "Fix Ratio"]
            interval_mins (int, optional): update interval. If -1 is specified, use frame of the client. Defaults to -1.
            data_length (int, optional): Length to caliculate the indicaters. Defaults to 250.
            logger (optional): You can pass your logger. Defaults to None.
        """
        
        ##initialize required columns
        self.bolinger_columns = bolinger_process.columns
        self.b_option = bolinger_process.option
        self.b_alpha = self.b_option["alpha"]
        if range_process is None or range_process.kinds != fc.utils.RangeTrendProcess.kinds:
            range_process = fc.utils.RangeTrendProcess()
        ## add BBANDPreProcess
        ##check if bolinger_process is an instannce of BBANDpreProcess
        super().__init__(finance_client, renko_process, macd_process, range_process, slope_window, self.b_alpha, amount, interval_mins, data_length, logger)

        self.client.add_indicater(bolinger_process)
        self.use_tp = use_tp
        self.column_dict = self.client.get_ohlc_columns()

        
    def run(self, long_short: int = None):
        df = self.client.get_rate_with_indicaters(self.data_length)
        signal = super().run(long_short, df)
        
        if self.use_tp:
            positions = self.client.get_positions()
            if len(positions) > 0:#if any position exists, check values to take profit
                width = df.iloc[-1][self.bolinger_columns["Width"]]
                unit_width = width/self.b_alpha
                order_price = None
                for position in positions:
                    if position.order_type == "ask":
                        bid_value = self.client.get_current_bid()
                        if signal is None:
                            order_price = bid_value#assign to pass the condition
                        else:
                            order_price = signal.order_price
                        upper_value = df.iloc[-1][self.bolinger_columns["UV"]]
                        if df.iloc[-1][self.column_dict["High"]] >= upper_value and bid_value >= upper_value - unit_width and bid_value >= order_price:
                            #signal = update_signal_with_close(signal, continuous_mode="long", std_name=self.key)
                            signal = update_signal_with_close(signal, std_name=self.key)
                            #self.logger.info("signal is updated with close as value is too high")
                        break#bidirectional order is not supported for this storategy
                    elif position.order_type == "bid":
                        #short position exists
                        ask_value = self.client.get_current_ask()
                        if signal is None:
                            order_price = ask_value#assign to pass the condition
                        else:
                            order_price = signal.order_price
                        lower_value = df.iloc[-1][self.bolinger_columns["LV"]]
                        if df.iloc[-1][self.column_dict["Low"]] <= lower_value and ask_value <= lower_value + unit_width and ask_value <= order_price:
                            self.logger.debug(f"org signal is {signal}")
                            signal = update_signal_with_close(signal, std_name=self.key)
                            #signal = update_signal_with_close(signal, continuous_mode="short", std_name=self.key)
                            self.logger.info("signal is updated with close as value is too low")
                            self.logger.debug(signal)
        
        #if signal is raised, check values for stop loss
        if signal is not None:
            #check bolinger band range
            lower_value = df.iloc[-1][self.bolinger_columns["LV"]]
            width = df[self.Width_column].iloc[-1]
            std = width/(self.alpha*2)
            if signal.is_buy is True:
                self.logger.info("buy signal is raised. Start adding a sl")
                signal.sl = signal.order_price - std*3
                    
            elif signal.is_buy is False:#sell case
                self.logger.info("sell signal is raised. Start adding a sl")
                signal.sl = signal.order_price + std*3
                    
            elif signal.is_close:
                pass
            
            else:            
                self.logger.error(f"unkown signal type {signal.is_buy}")
                signal = None
                self.trend = 0
                
        return signal
