import json

import finance_client as fc
import pandas as pd

from trade_strategy.signal import Signal

from .strategy_base import StrategyClient
from ..signal import *
from . import strategy


# Experimental. You may lose your money.
class SlopeChange(StrategyClient):
    key = "slope_change"

    def __init__(
        self,
        finance_client: fc.Client,
        slope_column,
        short_ema_column,
        long_ema_column,
        bb_width_column,
        rsi_column,
        idc_processes=[],
        interval_mins: int = -1,
        amount=1,
        data_length: int = 100,
        save_signal_info=False,
        order_price_column="close",
        slope_threshold=5,
        ema_threshold=0.1,
        rsi_threshold=70,
        logger=None,
    ) -> None:
        # TODO: add ema and slope if client doesn't have
        super().__init__(finance_client, idc_processes, interval_mins, amount, data_length, save_signal_info, logger)
        self.slope_column = slope_column
        self.short_ema_column = short_ema_column
        self.long_ema_column = long_ema_column
        self.bb_width_column = bb_width_column
        self.rsi_column = rsi_column
        self.ema_threshold = ema_threshold
        self.order_price_column = order_price_column
        self.slope_threshold = slope_threshold
        self.rsi_threshold = rsi_threshold
        self.__in_range = False

    @classmethod
    def get_required_idc_param_keys(self):
        return {}

    def get_signal(self, df, long_short: int = None, symbols=...) -> Signal:
        signal, self.__in_range = strategy.slope_change(
            long_short,
            df,
            slope_column=self.slope_column,
            short_ema_column=self.short_ema_column,
            long_ema_column=self.long_ema_column,
            bb_width_column=self.bb_width_column,
            rsi_column=self.rsi_column,
            amount=self.amount,
            order_price_column=self.order_price_column,
            slope_threshold=self.slope_threshold,
            ema_threshold=self.ema_threshold,
            rsi_threshold=self.rsi_threshold,
            in_range=self.__in_range,
        )
        return signal


class EMACross(StrategyClient):
    pass


class WMACross(StrategyClient):
    pass


class MACDCross(StrategyClient):
    key = "macd_cross"

    @classmethod
    def get_required_idc_param_keys(self):
        MACDProcessParamKey = "macd_process"
        return {fc.fprocess.MACDProcess.kinds: MACDProcessParamKey}

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

    def __init__(self, finance_client: fc.Client, macd_process=None, interval_mins: int = 30, data_length=100, logger=None) -> None:
        """When MACD cross up, return buy signal
            When MACD cross down, return sell signal

        Args:
            finance_client (fc.Client): data client
            interval_mins (int, optional): interval mins to get data. Defaults to -1.
            data_length (int, optional): length to caliculate the MACD. Defaults to 100.
            macd_process (Process, optional): You can specify specific parameter of MACD Process. Defaults to None.
        """
        super().__init__(finance_client, [], interval_mins, data_length, logger)
        if macd_process is None:
            macd = fc.fprocess.MACDProcess()
        else:
            if macd_process.kinds == "MACD":
                macd = macd_process
            else:
                raise Exception("MACDCross accept only MACDProcess")

        self.macd_column_name = macd.KEY_MACD
        self.signal_column_name = macd.KEY_SIGNAL
        column_dict = self.client.get_ohlc_columns()
        if type(column_dict) == dict:
            self.close_column_name = column_dict["Close"]
        else:
            self.close_column_name = "Close"
        self.current_trend = 0
        self.add_indicaters([macd])

    def get_signal(self, data, position, symbol: str):
        signal, tick_trend = strategy.macd_cross(
            position, self.current_trend, data, self.close_column_name, self.signal_column_name, self.macd_column_name
        )
        # save trend of macd
        self.current_trend = tick_trend
        return signal


class MACDRenko(StrategyClient):
    key = "macd_renko"

    @classmethod
    def get_required_idc_param_keys(self):
        RenkoProcessParamKey = "renko_process"
        MACDProcessParamKey = "macd_process"
        return {fc.fprocess.RenkoProcess.kinds: RenkoProcessParamKey, fc.fprocess.MACDProcess.kinds: MACDProcessParamKey}

    @classmethod
    def load(self, finance_client: fc.Client, idc_processes: list, options={}):
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

    def __init__(
        self,
        finance_client: fc.Client,
        renko_process: fc.fprocess.RenkoProcess,
        macd_process: fc.fprocess.MACDProcess,
        slope_window=5,
        amount=1,
        interval_mins: int = -1,
        data_length=250,
        threshold=2,
        logger=None,
        bolinger_threshold=None,
        rsi_threshold=None,
    ) -> None:
        super().__init__(finance_client, [], interval_mins, amount, data_length, logger)

        if renko_process is not None:
            if renko_process.kinds != "Renko":
                raise Exception("renko_process accept only RenkoProcess")
        else:
            ohlc_dict = finance_client.get_ohlc_columns()
            renko_process = fc.fprocess.RenkoProcess(ohlc_column=(ohlc_dict["Open"], ohlc_dict["High"], ohlc_dict["Low"], ohlc_dict["Close"]))
        if macd_process is not None:
            if macd_process.kinds != "MACD":
                raise Exception("macd_process accept only MACDProcess")
        else:
            ohlc_dict = finance_client.get_ohlc_columns()
            macd_process = fc.fprocess.MACDProcess(target_column=ohlc_dict["Close"])
        self.macd_column_column = macd_process.KEY_MACD
        self.macd_signal_column = macd_process.KEY_SIGNAL
        self.renko_bnum_column = renko_process.KEY_BRICK_NUM
        column_dict = self.client.get_ohlc_columns()
        self.threshold = threshold
        if type(column_dict) == dict:
            self.close_column_name = column_dict["Close"]
        else:
            self.close_column_name = "Close"

        macd_slope = fc.fprocess.SlopeProcess(key="m", target_column=self.macd_column_column, window=slope_window)
        signal_slope = fc.fprocess.SlopeProcess(key="s", target_column=self.macd_signal_column, window=slope_window)
        self.slope_macd_column = macd_slope.KEY_SLOPE
        self.slope_signal_column = signal_slope.KEY_SLOPE

        # when same key of process is already added, the process is ignored
        indicaters = [renko_process, macd_process, macd_slope, signal_slope]
        self.add_indicaters(indicaters)

        self.bolinger_threshold = bolinger_threshold
        if bolinger_threshold is not None:
            ohlc_dict = finance_client.get_ohlc_columns()
            b_process = fc.fprocess.BBANDProcess(alpha=bolinger_threshold, target_column=ohlc_dict["Close"])
            self.add_indicaters([b_process])
            self.bh_column = b_process.KEY_UPPER_VALUE
            self.bl_column = b_process.KEY_LOWER_VALUE
            self.order_price_column = ohlc_dict["Close"]
        self.rsi_threshold = rsi_threshold
        if rsi_threshold is not None:
            ohlc_dict = finance_client.get_ohlc_columns()
            rsi_p = fc.fprocess.RSIProcess(ohlc_column_name=list(ohlc_dict.values()))
            self.add_indicaters([rsi_p])
            rsi_column = rsi_p.KEY_RSI
            self.rsi_column = rsi_column

    def get_signal(self, df: pd.DataFrame, position, symbol: str):
        
        if position == 0:
            if self.bolinger_threshold is not None:
                current_price = df[self.order_price_column].iloc[-1]
                upper_price = df[self.bh_column].iloc[-1]
                if current_price >= upper_price:
                    return None
                else:
                    lower_price = df[self.bl_column].iloc[-1]
                    if current_price <= lower_price:
                        return None

            if self.rsi_threshold is not None:
                if self.rsi_column is not None:
                    rsi_value = abs(df[self.rsi_column].iloc[-1])
                    if rsi_value >= self.rsi_threshold[0]:
                        return None
                    elif rsi_value <= self.rsi_threshold[1]:
                        return None
                    
        signal = strategy.macd_renko(
            position,
            df,
            self.renko_bnum_column,
            self.macd_column_column,
            self.macd_signal_column,
            self.slope_macd_column,
            self.slope_signal_column,
            self.close_column_name,
            threshold=self.threshold,
        )
        return signal


class MACDRenkoSLByBB(MACDRenko):
    key = "bmacd_renko"

    @classmethod
    def get_required_idc_param_keys(self):
        RenkoProcessParamKey = "renko_process"
        MACDProcessParamKey = "macd_process"
        BBANDProcessParamKey = "bolinger_process"
        return {
            fc.fprocess.RenkoProcess.kinds: RenkoProcessParamKey,
            fc.fprocess.MACDProcess.kinds: MACDProcessParamKey,
            fc.fprocess.BBANDProcess.kinds: BBANDProcessParamKey,
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

    def __init__(
        self,
        finance_client: fc.Client,
        renko_process: fc.fprocess.RenkoProcess,
        macd_process: fc.fprocess.MACDProcess,
        bolinger_process: fc.fprocess.BBANDProcess,
        slope_window=5,
        amount=1,
        use_tp=False,
        interval_mins: int = -1,
        data_length=250,
        logger=None,
    ) -> None:
        """
        add condition to open a position by Bolinger Band

        Args:
            finance_client (fc.Client): Cliet
            renko_process (fc.fprocess.RenkoProcess): Renko Process of finance_client module
            macd_process (fc.fprocess.MACDpreProcess): MACD Process of finance_client module
            bolinger_process (fc.fprocess.BBANDpreProcess): BB Process of finance_client module
            slope_window (int, optional): window to caliculate window of the close. Defaults to 5.
            use_tp (bool, optional): Specify a method to add tp vaelue. If not to be specified, "none". Defaults to BB. ["BB", "none", "Fix Ratio"]
            interval_mins (int, optional): update interval. If -1 is specified, use frame of the client. Defaults to -1.
            data_length (int, optional): Length to caliculate the indicaters. Defaults to 250.
            logger (optional): You can pass your logger. Defaults to None.
        """
        ##check if bolinger_process is an instannce of BBANDpreProcess
        super().__init__(
            finance_client=finance_client,
            renko_process=renko_process,
            macd_process=macd_process,
            slope_window=slope_window,
            interval_mins=interval_mins,
            amount=amount,
            data_length=data_length,
            logger=logger,
        )

        self.add_indicaters([bolinger_process])

        # initialize required columns
        self.bolinger_columns = {
            "LV": bolinger_process.KEY_LOWER_VALUE,
            "MV": bolinger_process.KEY_MEAN_VALUE,
            "UV": bolinger_process.KEY_UPPER_VALUE,
        }
        self.b_option = bolinger_process.option
        self.b_alpha = self.b_option["alpha"]
        ## add BBANDPreProcess
        self.use_tp = use_tp
        self.column_dict = self.client.get_ohlc_columns()

    def get_signal(self, df: pd.DataFrame, position, symbol: str):
        ask_value = self.client.get_current_ask(symbol)
        bid_value = self.client.get_current_bid(symbol)
        signal = strategy.macd_renko_bb(
            position,
            df,
            self.renko_bnum_column,
            self.macd_column_column,
            self.macd_signal_column,
            self.slope_macd_column,
            self.slope_signal_column,
            self.close_column_name,
            self.bolinger_columns["LV"],
            self.bolinger_columns["MV"],
            self.bolinger_columns["UV"],
            ask_value,
            bid_value,
        )
        return signal


class CCICross(StrategyClient):
    key = "cci_cross"

    @classmethod
    def get_required_idc_param_keys(self):
        CCIProcessParamKey = "cci_process"
        return {
            fc.fprocess.CCIProcess.kinds: CCIProcessParamKey,
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

    def __init__(self, finance_client: fc.Client, cci_process=None, interval_mins: int = 30, data_length=100, logger=None) -> None:
        """Raise Buy/Sell signal when CCI cross up/down 0

        Args:
            finance_client (fc.Client): any finance_client
            cci_process (ProcessBase, optional): you can provide CCIProcess. Defaults to None and CCIProcess with default parameter is used.
            interval_mins (int, optional): interval minutes to get_signal this strategy. Defaults to 30.
            data_length (int, optional): data length to caliculate CCI. Defaults to 100.
            logger (Logger, optional): you can specify your logger. Defaults to None.

        Raises:
            Exception: when other than CCI process is provided.
        """
        super().__init__(finance_client, [], interval_mins, data_length, logger)
        if cci_process == None:
            cci_process = fc.fprocess.CCIProcess()
        else:
            if cci_process.kinds != "CCI":
                raise Exception("CCICross accept only CCIProcess")

        self.cci_column_name = cci_process.KEY_CCI
        column_dict = self.client.get_ohlc_columns()
        if type(column_dict) == dict:
            self.close_column_name = column_dict["Close"]
        else:
            self.close_column_name = "Close"
        self.logger.info(f"initialized cci strategy")
        indicaters = [cci_process]
        df = self.client.get_ohlc(self.data_length, idc_processes=indicaters)
        last_df = df.iloc[-1]
        current_cci = last_df[self.cci_column_name]
        if current_cci > 0:
            self.trend = LongTrend()
        else:
            self.trend = ShortTrend()
        self.add_indicaters(indicaters)

    def get_signal(self, df: pd.DataFrame, position, symbol: str):
        signal = strategy.cci_cross(position, df, self.cci_column_name, self.close_column_name)
        return signal


class CCIBoader(StrategyClient):
    key = "cci_boader"

    @classmethod
    def get_required_idc_param_keys(self):
        CCIProcessParamKey = "cci_process"
        return {
            fc.fprocess.CCIProcess.kinds: CCIProcessParamKey,
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

    def __init__(
        self, finance_client: fc.Client, cci_process=None, upper=100, lower=-100, interval_mins: int = 30, data_length=100, logger=None
    ) -> None:
        """Raise Buy/Sell signal when CCI cross up/down uppser/lower

        Args:
            finance_client (fc.Client): any finance_client
            cci_process (ProcessBase, optional): you can provide CCIProcess. Defaults to None and CCIProcess with default parameter is used.
            upper (int, option): upper value to raise Buy Signal. Defaults to 100
            lower (int, option): lower value to raise Sell Signal. Defaults to -100
            interval_mins (int, optional): interval minutes to get_signal this strategy. Defaults to 30.
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
            cci_process = fc.fprocess.CCIProcess()
        else:
            if cci_process.kinds != "CCI":
                raise Exception("CCICross accept only CCIProcess")

        self.cci_column_name = cci_process.KEY_CCI
        column_dict = self.client.get_ohlc_columns()
        if type(column_dict) == dict:
            self.close_column_name = column_dict["Close"]
        else:
            self.close_column_name = "Close"
        self.logger.info(f"initialized cci strategy")
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

    def get_signal(self, df: pd.DataFrame, position, symbol: str):
        signal = strategy.cci_boader(position, df, self.cci_column_name, self.close_column_name, self.upper, self.lower)
        return signal


class RangeTrade(StrategyClient):
    key = "range"

    @classmethod
    def get_required_idc_param_keys(self):
        RangeProcessParamKey = "range_process"
        return {
            fc.fprocess.RangeTrendProcess.kinds: RangeProcessParamKey,
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

    def __init__(
        self,
        finance_client: fc.Client,
        range_process=None,
        alpha=1,
        slope_ratio=0.4,
        interval_mins: int = -1,
        amount=1,
        data_length: int = 100,
        logger=None,
    ) -> None:
        super().__init__(finance_client, [], interval_mins, amount, data_length, logger)
        ohlc_columns = finance_client.get_ohlc_columns()
        self.close_column = ohlc_columns["Close"]
        self.high_column = ohlc_columns["High"]
        self.low_column = ohlc_columns["Low"]
        if range_process is None:
            range_process = fc.fprocess.RangeTrendProcess()
        bband_process = fc.fprocess.BBANDProcess(target_column=self.close_column, alpha=alpha)
        indicaters = [bband_process, range_process]
        ##initialize params of range indicater
        temp = finance_client.do_render
        finance_client.do_render = False
        finance_client.get_ohlc(idc_processes=indicaters)
        finance_client.do_render = temp
        self.trend_possibility_column = range_process.KEY_TREND
        self.range_possibility_column = range_process.KEY_RANGE
        self.width_column = bband_process.KEY_WIDTH_VALUE
        self.UV_column = bband_process.KEY_UPPER_VALUE
        self.LV_column = bband_process.KEY_LOWER_VALUE
        self.MV_column = bband_process.KEY_MEAN_VALUE
        self.alpha = alpha
        self.__tp_threrad = slope_ratio
        self.add_indicaters(indicaters)

    def get_signal(self, df: pd.DataFrame, position, symbol: str):
        signal = strategy.range_experimental(
            position,
            df,
            self.range_possibility_column,
            self.trend_possibility_column,
            self.width_column,
            self.alpha,
            self.__tp_threrad,
            self.close_column,
        )
        return signal


class MACDRenkoRange(StrategyClient):
    key = "macd_ranko_range"

    @classmethod
    def get_required_idc_param_keys(self):
        RangeProcessParamKey = "range_process"
        RenkoProcessParamKey = "renko_process"
        MACDProcessParamKey = "macd_process"
        return {
            fc.fprocess.RenkoProcess.kinds: RenkoProcessParamKey,
            fc.fprocess.RangeTrendProcess.kinds: RangeProcessParamKey,
            fc.fprocess.MACDProcess.kinds: MACDProcessParamKey,
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

    def __init__(
        self,
        finance_client: fc.Client,
        renko_process: fc.fprocess.RenkoProcess,
        macd_process: fc.fprocess.MACDProcess,
        range_process: fc.fprocess.RangeTrendProcess,
        bolinger_process=None,
        slope_window=5,
        alpha=2,
        amount=1,
        interval_mins: int = -1,
        data_length=250,
        threshold=2,
        logger=None,
    ) -> None:
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

        self.threshold = threshold
        self.__is_in_range = False

        if range_process is None or range_process.kinds != fc.fprocess.RangeTrendProcess.kinds:
            range_process = fc.fprocess.RangeTrendProcess()
        if bolinger_process is None:
            bband_process = fc.fprocess.BBANDProcess(target_column=self.close_column_name, alpha=alpha)
        else:
            bband_process = bolinger_process
        self.alpha = alpha
        self.macd_column_column = macd_process.KEY_MACD
        self.macd_signal_column = macd_process.KEY_SIGNAL
        self.renko_bnum_column = renko_process.KEY_BRICK_NUM

        macd_slope = fc.fprocess.SlopeProcess(key="m", target_column=self.macd_column_column, window=slope_window)
        signal_slope = fc.fprocess.SlopeProcess(key="s", target_column=self.macd_signal_column, window=slope_window)
        self.slope_macd_column = macd_slope.KEY_SLOPE
        self.slope_signal_column = signal_slope.KEY_SLOPE
        self.trend_possibility_column = range_process.KEY_TREND
        self.range_possibility_column = range_process.KEY_RANGE
        self.Width_column = bband_process.KEY_WIDTH_VALUE
        self.BHigh_column = bband_process.KEY_UPPER_VALUE
        self.BLow_column = bband_process.KEY_LOWER_VALUE
        self.add_indicaters([renko_process, bband_process, macd_process, macd_slope, signal_slope, range_process])

    def get_signal(self, df: pd.DataFrame, position, symbol: str):
        signal, self.__is_in_range = strategy.macd_renko_range_ex(
            position,
            df,
            self.__is_in_range,
            self.range_possibility_column,
            self.renko_bnum_column,
            self.macd_column_column,
            self.macd_signal_column,
            self.slope_macd_column,
            self.slope_signal_column,
            self.high_column_name,
            self.BHigh_column,
            self.low_column_name,
            self.BLow_column,
            self.threshold,
            self.close_column_name,
        )
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
            fc.fprocess.RenkoProcess.kinds: RenkoProcessParamKey,
            fc.fprocess.RangeTrendProcess.kinds: RangeProcessParamKey,
            fc.fprocess.MACDProcess.kinds: MACDProcessParamKey,
            fc.fprocess.BBANDProcess.kinds: BBANDProcessParamKey,
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

    def __init__(
        self,
        finance_client: fc.Client,
        renko_process: fc.fprocess.RenkoProcess,
        macd_process: fc.fprocess.MACDProcess,
        bolinger_process: fc.fprocess.BBANDProcess,
        range_process=None,
        slope_window=5,
        alpha=2,
        amount=1,
        use_tp=False,
        interval_mins: int = -1,
        data_length=250,
        threshold=2,
        logger=None,
        bolinger_threshold=None,
        rsi_column=None,
        rsi_threshold=None,
    ) -> None:
        """
        add condition to open a position by Bolinger Band

        Args:
            finance_client (fc.Client): Cliet
            renko_process (fc.fprocess.RenkoProcess): Renko Process of finance_client module
            macd_process (fc.fprocess.MACDpreProcess): MACD Process of finance_client module
            bolinger_process (fc.fprocess.BBANDpreProcess): BB Process of finance_client module
            slope_window (int, optional): window to caliculate window of the MACD and Signal. Defaults to 5.
            use_tp (bool, optional): take profit based on twice value of stop loss (experimental)
            interval_mins (int, optional): update interval. If -1 is specified, use frame of the client. Defaults to -1.
            data_length (int, optional): Length to caliculate the indicaters. Defaults to 250.
            logger (optional): You can pass your logger. Defaults to None.
            bolinger_threshold (float) : threthold to return None based on bolinger std with alpha=1. Specify multiply value of std, defaults to None
            rsi_column (str): column to determin current rsi for threshold,
            rsi_threshold (float): threthold to return None based on rsi. Specify a boader value, defaults to None
        """

        # initialize required columns
        self.bolinger_columns = bolinger_process.columns
        if range_process is None or range_process.kinds != fc.fprocess.RangeTrendProcess.kinds:
            range_process = fc.fprocess.RangeTrendProcess()
        self.bolinger_threshold = bolinger_threshold
        self.rsi_threshold = rsi_threshold
        if rsi_threshold is not None:
            if rsi_column is None:
                rsi_p = fc.fprocess.RSIProcess()
                self.add_indicaters([rsi_p])
                rsi_column = rsi_p.KEY_RSI
        self.rsi_column = rsi_column

        # add BBANDPreProcess
        # check if bolinger_process is an instannce of BBANDpreProcess
        super().__init__(
            finance_client,
            renko_process,
            macd_process,
            range_process,
            bolinger_process=bolinger_process,
            slope_window=slope_window,
            alpha=alpha,
            amount=amount,
            interval_mins=interval_mins,
            data_length=data_length,
            threshold=threshold,
            logger=logger,
        )

        self.use_tp = use_tp
        self.column_dict = self.client.get_ohlc_columns()
        self.__is_in_range = False

    def get_signal(self, df: pd.DataFrame, position, symbol: str):
        signal, self.__is_in_range = strategy.macd_renkorange_bb_ex(
            position,
            df,
            self.__is_in_range,
            self.range_possibility_column,
            self.renko_bnum_column,
            self.macd_column_column,
            self.macd_signal_column,
            self.slope_macd_column,
            self.slope_signal_column,
            self.high_column_name,
            self.BHigh_column,
            self.low_column_name,
            self.BLow_column,
            self.Width_column,
            self.alpha,
            self.threshold,
            self.close_column_name,
            self.use_tp,
            bolinger_threshold=self.bolinger_threshold,
            rsi_column=self.rsi_column,
            rsi_threshold=self.rsi_threshold,
        )
        return signal


class Momentum(StrategyClient):
    key = "atrsma"

    def __init__(
        self,
        finance_client: fc.Client,
        momentum_column,
        short_ma_column,
        atr_column,
        order_price_column="Close",
        baseline_column=None,
        baseline_ma_column=None,
        threshold=0.2,
        risk_factor=0.001,
        idc_processes=...,
        interval_mins: int = -1,
        amount=1,
        data_length: int = 100,
        save_signal_info=False,
        logger=None,
    ) -> None:
        self.momentum_column = momentum_column
        self.short_ma_column = short_ma_column
        self.atr_column = atr_column
        self.order_price_column = order_price_column
        self.baseline_column = baseline_column
        self.baseline_ma_column = baseline_ma_column
        self.threshold = threshold
        self.risk_factor = risk_factor
        super().__init__(finance_client, idc_processes, interval_mins, amount, data_length, save_signal_info, logger)

    def get_signals(self, df, positions, symbols):
        signals = strategy.momentum_ma(
            positions,
            df,
            self.amount,
            self.momentum_column,
            self.short_ma_column,
            self.atr_column,
            self.order_price_column,
            self.baseline_column,
            self.baseline_ma_column,
            self.threshold,
            self.risk_factor,
        )
        return signals
