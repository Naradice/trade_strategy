from trade_storategy.storategies.strategy_base import StorategyClient
from trade_storategy.signal import *
from . import storategy
import finance_client as fc
import json
import pandas as pd

## TODO: caliculate required length from idc_processes

class EMACross(StorategyClient):
    pass

class WMACross(StorategyClient):
    pass

class MACDCross(StorategyClient):
    
    key = "macd_cross"    
    
    @classmethod
    def get_required_idc_param_keys(self):
        MACDProcessParamKey = "macd_process"
        return {
            fc.utils.MACDProcess.kinds: MACDProcessParamKey
        }
    
    @classmethod
    def load(self, finance_client, idc_processes=[], options={}):
        required_process_keys = self.get_required_idc_param_keys()
        
        idc_options = {}
        for key, item in required_process_keys.items():
            idc_options[item] = None
        for process in idc_processes:
            if process.kinds in required_process_keys:
                param_key = required_process_keys[process.kinds]
                idc_options[param_key] = process
        options.update(idc_options)
        return MACDCross(finance_client=finance_client, **options)
    
    def __init__(self, finance_client: fc.Client, macd_process = None, interval_mins: int = 30, data_length=100, logger=None) -> None:
        """ When MACD cross up, return buy signal
            When MACD cross down, return sell signal

        Args:
            finance_client (fc.Client): data client
            interval_mins (int, optional): interval mins to get data. Defaults to -1.
            data_length (int, optional): length to caliculate the MACD. Defaults to 100.
            macd_process (Process, optional): You can specify specific parameter of MACD Process. Defaults to None.
        """
        super().__init__(finance_client, [], interval_mins, data_length, logger)
        if macd_process is None:
            macd = fc.utils.MACDProcess()
        else:
            if macd.kinds == "MACD":
                macd = macd_process
            else:
                raise Exception("MACDCross accept only MACDProcess")
            
        self.macd_column_name = macd.columns["MACD"]
        self.signal_column_name = macd.columns["Signal"]
        column_dict = self.client.get_ohlc_columns()
        if type(column_dict) == dict:
            self.close_column_name = column_dict["Close"]
        else:
            self.close_column_name = "Close"
        self.current_trend = 0
        self.add_indicaters([macd])
            
    def get_signal(self, data, position):
        signal, tick_trend = storategy.macd_cross(position, self.current_trend,data, self.close_column_name, self.signal_column_name,
                             self.macd_column_name)
        #save trend of macd
        self.current_trend = tick_trend
        return signal
        
class MACDRenko(StorategyClient):
    
    key="macd_renko"
    
    @classmethod
    def get_required_idc_param_keys(self):
        RenkoProcessParamKey = "renko_process"
        MACDProcessParamKey = "macd_process"
        return {
            fc.utils.RenkoProcess.kinds: RenkoProcessParamKey,
            fc.utils.MACDProcess.kinds: MACDProcessParamKey
        }
    
    @classmethod
    def load(self, finance_client: fc.Client, idc_processes:list, options={}):
        required_process_keys = self.get_required_idc_param_keys()
        idc_options = {}
        for key, item in required_process_keys.items():
            idc_options[item] = None
        for process in idc_processes:
            if process.kinds in required_process_keys:
                param_key = required_process_keys[process.kinds]
                idc_options[param_key] = process
        options.update(idc_options)
        return MACDRenko(finance_client=finance_client, **options)
        
    
    def __init__(self, finance_client: fc.Client, renko_process: fc.utils.RenkoProcess, macd_process: fc.utils.MACDProcess, slope_window = 5, amount=1, interval_mins: int = -1, data_length=250, logger=None) -> None:
        super().__init__(finance_client, [], interval_mins, amount, data_length, logger)
        
        if renko_process is not None:
            if renko_process.kinds != "Renko":
                raise Exception("renko_process accept only RenkoProcess")
        else:
            ohlc_dict = finance_client.get_ohlc_columns()
            renko_process = fc.utils.RenkoProcess(ohlc_column=(ohlc_dict["Open"], ohlc_dict["High"], ohlc_dict["Low"], ohlc_dict["Close"]))
        if macd_process is not None:
            if macd_process.kinds != "MACD":
                raise Exception("macd_process accept only MACDProcess")
        else:
            ohlc_dict = finance_client.get_ohlc_columns()
            macd_process = fc.utils.MACDProcess(target_column=ohlc_dict["Close"])
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
        
        #when same key of process is already added, the process is ignored
        indicaters = [renko_process, macd_process, macd_slope, signal_slope]
        self.add_indicaters(indicaters)

    def get_signal(self, df:pd.DataFrame, position):
        signal = storategy.macd_renko(position, df, self.renko_bnum_column, self.macd_column_column, self.macd_signal_column, self.slope_macd_column,
                             self.slope_signal_column, self.close_column_name)
        return signal
    
class MACDRenkoSLByBB(MACDRenko):
    
    key = "bmacd_renko"
    
    @classmethod
    def get_required_idc_param_keys(self):
        RenkoProcessParamKey = "renko_process"
        MACDProcessParamKey = "macd_process"
        BBANDProcessParamKey = "bolinger_process"
        return {
            fc.utils.RenkoProcess.kinds: RenkoProcessParamKey,
            fc.utils.MACDProcess.kinds: MACDProcessParamKey,
            fc.utils.BBANDProcess.kinds: BBANDProcessParamKey
        }
        
    
    @classmethod
    def load(self, finance_client, idc_processes=[], options={}):
        required_process_keys = self.get_required_idc_param_keys()
        
        idc_options = {}
        for key, item in required_process_keys.items():
            idc_options[item] = None
        for process in idc_processes:
            if process.kinds in required_process_keys:
                param_key = required_process_keys[process.kinds]
                idc_options[param_key] = process
        options.update(idc_options)
        return MACDRenkoRangeSLByBB(finance_client, **options)
    
    def __init__(self, finance_client: fc.Client, renko_process: fc.utils.RenkoProcess, macd_process: fc.utils.MACDProcess, bolinger_process:fc.utils.BBANDProcess, slope_window = 5, amount=1, use_tp= False, continuous=False, interval_mins: int = -1, data_length=250, logger=None) -> None:
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
        self.use_tp = use_tp
        self.column_dict = self.client.get_ohlc_columns()

    def get_signal(self, df:pd.DataFrame, position):
        ask_value = self.client.get_current_ask()
        bid_value = self.client.get_current_bid()
        signal = storategy.macd_renko_bb(position, df, self.renko_bnum_column, self.macd_column_column, self.macd_signal_column, self.slope_macd_column
                                , self.slope_signal_column, self.close_column_name, self.bolinger_columns["LV"], self.bolinger_columns["MV"],
                                self.bolinger_columns["UV"], ask_value, bid_value)
        return signal

class CCICross(StorategyClient):
    
    key = "cci_cross"
    
    @classmethod
    def get_required_idc_param_keys(self):
        CCIProcessParamKey = "cci_process"
        return {
            fc.utils.CCIProcess.kinds: CCIProcessParamKey,
        }
    
    @classmethod
    def load(self, finance_client, idc_processes=[], options={}):
        required_process_keys = self.get_required_idc_param_keys()
        
        idc_options = {}
        for key, item in required_process_keys.items():
            idc_options[item] = None
        for process in idc_processes:
            if process.kinds in required_process_keys:
                param_key = required_process_keys[process.kinds]
                idc_options[param_key] = process
        options.update(idc_options)
        return CCICross(finance_client, **options)
    
    def __init__(self, finance_client: fc.Client, cci_process = None, interval_mins: int = 30, data_length=100, logger=None) -> None:
        """ Raise Buy/Sell signal when CCI cross up/down 0

        Args:
            finance_client (fc.Client): any finance_client
            cci_process (ProcessBase, optional): you can provide CCIProcess. Defaults to None and CCIProcess with default parameter is used.
            interval_mins (int, optional): interval minutes to get_signal this storategy. Defaults to 30.
            data_length (int, optional): data length to caliculate CCI. Defaults to 100.
            logger (Logger, optional): you can specify your logger. Defaults to None.

        Raises:
            Exception: when other than CCI process is provided.
        """
        super().__init__(finance_client, [], interval_mins, data_length, logger)
        if cci_process == None:
            cci_process = fc.utils.CCIProcess()
        else:
            if cci_process.kinds != "CCI":
                raise Exception("CCICross accept only CCIProcess")
            
        self.cci_column_name = cci_process.columns["CCI"]
        column_dict = self.client.get_ohlc_columns()
        if type(column_dict) == dict:
            self.close_column_name = column_dict["Close"]
        else:
            self.close_column_name = "Close"
        self.logger.info(f"initialized cci storategy")
        indicaters = [cci_process]
        df = self.client.get_ohlc(self.data_length, idc_processes=indicaters)
        last_df = df.iloc[-1]
        current_cci = last_df[self.cci_column_name]
        if current_cci > 0:
            self.trend = LongTrend()
        else:
            self.trend = ShortTrend()
        self.add_indicaters(indicaters)
            
    def get_signal(self, df:pd.DataFrame, position=None):
        signal = storategy.cci_cross(position, df, self.cci_column_name, self.close_column_name)
        return signal
    
class CCIBoader(StorategyClient):
    
    key = "cci_boader"
    
    @classmethod
    def get_required_idc_param_keys(self):
        CCIProcessParamKey = "cci_process"
        return {
            fc.utils.CCIProcess.kinds: CCIProcessParamKey,
        }
    
    @classmethod
    def load(self, finance_client, idc_processes=[], options={}):
        required_process_keys = self.get_required_idc_param_keys()
        
        idc_options = {}
        for key, item in required_process_keys.items():
            idc_options[item] = None
        for process in idc_processes:
            if process.kinds in required_process_keys:
                param_key = required_process_keys[process.kinds]
                idc_options[param_key] = process
        options.update(idc_options)
        return CCIBoader(finance_client, **options)    
    
    def __init__(self, finance_client: fc.Client, cci_process = None, upper=100, lower = -100, interval_mins: int = 30, data_length=100, logger=None) -> None:
        """ Raise Buy/Sell signal when CCI cross up/down uppser/lower

        Args:
            finance_client (fc.Client): any finance_client
            cci_process (ProcessBase, optional): you can provide CCIProcess. Defaults to None and CCIProcess with default parameter is used.
            upper (int, option): upper value to raise Buy Signal. Defaults to 100
            lower (int, option): lower value to raise Sell Signal. Defaults to -100
            interval_mins (int, optional): interval minutes to get_signal this storategy. Defaults to 30.
            data_length (int, optional): data length to caliculate CCI. Defaults to 100.
            logger (Logger, optional): you can specify your logger. Defaults to None.

        Raises:
            Exception: when other than CCI process is provided.
            ValueException: when lower >= upper
        """
        super().__init__(finance_client, [], interval_mins, data_length, logger)
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
            
        self.cci_column_name = cci_process.columns["CCI"]
        column_dict = self.client.get_ohlc_columns()
        if type(column_dict) == dict:
            self.close_column_name = column_dict["Close"]
        else:
            self.close_column_name = "Close"
        self.logger.info(f"initialized cci storategy")
        indicaters = [cci_process]
        df = self.client.get_ohlc(self.data_length, idc_processes=indicaters)
        last_df = df.iloc[-1]
        current_cci = last_df[self.cci_column_name]
        if current_cci >= upper:
            self.trend = LongTrend()
        elif current_cci <= lower:
            self.trend = ShortTrend()
        else:
            self.trend = Trend()
        self.add_indicaters(indicaters)
            
    def get_signal(self, df:pd.DataFrame, position):
        signal = storategy.cci_boader(position, df, self.cci_column_name, self.close_column_name, self.upper, self.lower)        
        return signal
    
class RangeTrade(StorategyClient):
    
    key = "range"
    
    @classmethod
    def get_required_idc_param_keys(self):
        RangeProcessParamKey = "range_process"
        return {
            fc.utils.RangeTrendProcess.kinds: RangeProcessParamKey,
        }
    
    @classmethod
    def load(self, finance_client, idc_processes=[], options={}):
        required_process_keys = self.get_required_idc_param_keys()
        
        idc_options = {}
        for key, item in required_process_keys.items():
            idc_options[item] = None
        for process in idc_processes:
            if process.kinds in required_process_keys:
                param_key = required_process_keys[process.kinds]
                idc_options[param_key] = process
        options.update(idc_options)
        return CCICross(finance_client, **options)
    
    def __init__(self, finance_client: fc.Client, range_process=None, alpha=1, slope_ratio=0.4, interval_mins: int = -1, amount=1, data_length: int = 100, logger=None) -> None:
        super().__init__(finance_client, [], interval_mins, amount, data_length, logger)
        ohlc_columns = finance_client.get_ohlc_columns()
        self.close_column = ohlc_columns["Close"]
        self.high_column = ohlc_columns["High"]
        self.low_column = ohlc_columns["Low"]
        if range_process is None:
            range_process = fc.utils.RangeTrendProcess()
        bband_process = fc.utils.BBANDProcess(target_column=self.close_column, alpha=alpha)
        indicaters = [bband_process, range_process]
        ##initialize params of range indicater
        temp = finance_client.do_render
        finance_client.do_render = False
        finance_client.get_ohlc(idc_processes=indicaters)
        finance_client.do_render = temp
        self.trend_possibility_column = range_process.columns["trend"]
        self.range_possibility_column = range_process.columns["range"]
        self.width_column = bband_process.columns["Width"]
        self.UV_column = bband_process.columns["UV"]
        self.LV_column = bband_process.columns["LV"]
        self.MV_column = bband_process.columns["MV"]
        self.alpha = alpha
        self.__tp_threrad = slope_ratio
        self.add_indicaters(indicaters)
        
    def get_signal(self, df:pd.DataFrame, position):
        signal = storategy.range_experimental(position, df, self.range_possibility_column, self.trend_possibility_column,
                                              self.width_column, self.alpha, self.__tp_threrad, self.close_column)
        return signal
         
class MACDRenkoRange(StorategyClient):
    
    key="macd_ranko_range"
    
    @classmethod
    def get_required_idc_param_keys(self):
        RangeProcessParamKey = "range_process"
        RenkoProcessParamKey = "renko_process"
        MACDProcessParamKey = "macd_process"
        return {
            fc.utils.RenkoProcess.kinds: RenkoProcessParamKey,
            fc.utils.RangeTrendProcess.kinds: RangeProcessParamKey,
            fc.utils.MACDProcess.kinds: MACDProcessParamKey
        }
    
    @classmethod
    def load(self, finance_client, idc_processes=[], options={}):
        required_process_keys = self.get_required_idc_param_keys()
        
        idc_options = {}
        for key, item in required_process_keys.items():
            idc_options[item] = None
        for process in idc_processes:
            if process.kinds in required_process_keys:
                param_key = required_process_keys[process.kinds]
                idc_options[param_key] = process
        options.update(idc_options)
        return MACDRenkoRange(finance_client, **options)
    
    def __init__(self, finance_client: fc.Client, renko_process: fc.utils.RenkoProcess, macd_process: fc.utils.MACDProcess, range_process: fc.utils.RangeTrendProcess, slope_window = 5, alpha=2, amount=1, interval_mins: int = -1, data_length=250, logger=None) -> None:
        super().__init__(finance_client, [], interval_mins, amount, data_length, logger)
        
        if renko_process.kinds != "Renko":
            raise Exception("renko_process accept only RenkoProcess")
            
        if macd_process.kinds != "MACD":
            raise Exception("macd_process accept only MACDProcess")
        
        column_dict = self.client.get_ohlc_columns()
        if type(column_dict) == dict:
            self.close_column_name = column_dict["Close"]
            self.high_column_name = column_dict["High"]
            self.low_column_name = column_dict["Low"]
        else:
            self.close_column_name = "Close"
            self.high_column_name = "High"
            self.low_column_name = "Low"
        
        self.__is_in_range = False

        if range_process is None or range_process.kinds != fc.utils.RangeTrendProcess.kinds:
            range_process = fc.utils.RangeTrendProcess()
        bband_process = fc.utils.BBANDProcess(target_column=self.close_column_name, alpha=alpha)
        self.alpha = alpha
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
        self.BHigh_column = bband_process.columns["UV"]
        self.BLow_column = bband_process.columns["LV"]
        self.add_indicaters([renko_process, bband_process, macd_process, macd_slope, signal_slope, range_process])

            
    def get_signal(self, df:pd.DataFrame, position):
        signal, self.__is_in_range = storategy.macd_renko_range_ex(position, df, self.__is_in_range,
                self.range_possibility_column, self.renko_bnum_column,
                self.macd_column_column, self.macd_signal_column, self.slope_macd_column, self.slope_signal_column,
                self.high_column_name, self.BHigh_column, self.low_column_name, self.BLow_column, self.close_column_name)
        return signal
    
class MACDRenkoRangeSLByBB(MACDRenkoRange):
    
    key = "bmacd_renkor"
    
    @classmethod
    def get_required_idc_param_keys(self):
        RangeProcessParamKey = "range_process"
        RenkoProcessParamKey = "renko_process"
        MACDProcessParamKey = "macd_process"
        BBANDProcessParamKey = "bolinger_process"
        return {
            fc.utils.RenkoProcess.kinds: RenkoProcessParamKey,
            fc.utils.RangeTrendProcess.kinds: RangeProcessParamKey,
            fc.utils.MACDProcess.kinds: MACDProcessParamKey,
            fc.utils.BBANDProcess.kinds: BBANDProcessParamKey
        }
    
    @classmethod
    def load(self, finance_client, idc_processes=[], options={}):
        required_process_keys = self.get_required_idc_param_keys()
        
        idc_options = {}
        for key, item in required_process_keys.items():
            idc_options[item] = None 
        for process in idc_processes:
            if process.kinds in required_process_keys:
                param_key = required_process_keys[process.kinds]
                idc_options[param_key] = process
        options.update(idc_options)
        return MACDRenkoRangeSLByBB(finance_client, **options)
    
    def __init__(self, finance_client: fc.Client, renko_process: fc.utils.RenkoProcess, macd_process: fc.utils.MACDProcess, bolinger_process:fc.utils.BBANDProcess, range_process=None, slope_window = 5, amount=1, use_tp= False, interval_mins: int = -1, data_length=250, logger=None) -> None:
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

        self.use_tp = use_tp
        self.column_dict = self.client.get_ohlc_columns()
        self.__is_in_range = False
    
    def get_signal(self, df:pd.DataFrame, position):
        signal, self.__is_in_range = storategy.macd_renkorange_bb_ex(position, df, self.__is_in_range,
                                                 self.range_possibility_column, self.renko_bnum_column,
                                                 self.macd_column_column, self.macd_signal_column, self.slope_macd_column, self.slope_signal_column,
                                                 self.high_column_name, self.BHigh_column, self.low_column_name, self.BLow_column,
                                                 self.Width_column, self.alpha, self.close_column_name)
        return signal