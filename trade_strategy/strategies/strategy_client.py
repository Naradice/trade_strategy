import finance_client as fc
import pandas as pd
from finance_client import utils, Position
from typing import List, List, Union

from trade_strategy.signal import Signal

from .strategy_base import StrategyClient
from ..signal import *
from . import strategy

# Experimental. You may lose your money.
class SlopeChange(StrategyClient):
    key = "slope_change"

    def __init__(
        self,
        finance_client: fc.ClientBase,
        slope_column,
        short_ema_column,
        long_ema_column,
        bb_width_column,
        rsi_column,
        idc_processes=[],
        interval_mins: int = -1,
        volume=1,
        data_length: int = 100,
        save_signal_info=False,
        order_price_column="close",
        slope_threshold=5,
        ema_threshold=0.1,
        rsi_threshold=70,
        trailing_stop=None,
        logger=None,
    ) -> None:
        # TODO: add ema and slope if client doesn't have
        super().__init__(finance_client, idc_processes, interval_mins, volume, data_length, trailing_stop, save_signal_info, logger)
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

    def get_signal(self, df, position: Position = None, symbols=...) -> Signal:
        signal, self.__in_range = strategy.slope_change(
            position,
            df,
            slope_column=self.slope_column,
            short_ema_column=self.short_ema_column,
            long_ema_column=self.long_ema_column,
            bb_width_column=self.bb_width_column,
            rsi_column=self.rsi_column,
            volume=self.volume,
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

    def __init__(self, finance_client: fc.ClientBase, macd_process=None, volume=1,
                 ohlc_columns=None,
                 interval_mins: int = 30, data_length=100, trailing_stop=None, logger=None) -> None:
        """When MACD cross up, return buy signal
            When MACD cross down, return sell signal

        Args:
            finance_client (fc.Client): data client
            interval_mins (int, optional): interval mins to get data. Defaults to -1.
            data_length (int, optional): length to caliculate the MACD. Defaults to 100.
            macd_process (Process, optional): You can specify specific parameter of MACD Process. Defaults to None.
            volume (int, optional): The volume for the trade signals. Defaults to 1.
        """
        super().__init__(finance_client, [], interval_mins, volume=volume, data_length=data_length,
                          trailing_stop=trailing_stop, logger=logger)
        if macd_process is None:
            if ohlc_columns is not None:
                target_column = ohlc_columns[-1]
            macd = fc.fprocess.MACDProcess(target_column=target_column if ohlc_columns is not None else "Close")
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
        self.volume = volume
        self.add_indicaters([macd])

    def get_signal(self, data, position: Position = None, symbol: str = None):
        signal, tick_trend = strategy.macd_cross(
            position, self.current_trend, data, self.close_column_name, self.signal_column_name, self.macd_column_name
        )
        if signal is not None:
            signal.volume = self.volume
            signal.symbol = symbol
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
    def load(self, finance_client: fc.ClientBase, idc_processes: list, options={}):
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
        finance_client: fc.ClientBase,
        renko_process: fc.fprocess.RenkoProcess,
        macd_process: fc.fprocess.MACDProcess,
        volume=1,
        interval_mins: int = -1,
        data_length=250,
        threshold=2,
        slope_window=None,
        logger=None,
        renko_brick_size=None,
        renko_window=None,
        trailing_stop=None,
        range_function=None,
    ) -> None:
        super().__init__(finance_client, [], interval_mins, volume, data_length, trailing_stop=trailing_stop, logger=logger)

        if renko_process is not None:
            if renko_process.kinds != "Renko":
                raise Exception("renko_process accept only RenkoProcess")
        else:
            ohlc_dict = finance_client.get_ohlc_columns()
            renko_process = fc.fprocess.RenkoProcess(
                ohlc_column=(ohlc_dict["Open"], ohlc_dict["High"], ohlc_dict["Low"], ohlc_dict["Close"]),
                brick_size=renko_brick_size,
                window=renko_window,
            )
        if macd_process is not None:
            if macd_process.kinds != "MACD":
                raise Exception("macd_process accept only MACDProcess")
        else:
            ohlc_dict = finance_client.get_ohlc_columns()
            macd_process = fc.fprocess.MACDProcess(target_column=ohlc_dict["Close"])
        self.macd_column_column = macd_process.KEY_MACD
        self.macd_signal_column = macd_process.KEY_SIGNAL
        self.renko_bnum_column = renko_process.KEY_VALUE
        column_dict = self.client.get_ohlc_columns()
        self.threshold = threshold
        if type(column_dict) == dict:
            self.close_column_name = column_dict["Close"]
        else:
            self.close_column_name = "Close"

        # when same key of process is already added, the process is ignored
        indicaters = [renko_process, macd_process]

        if slope_window is not None and slope_window > 0:
            macd_slope = fc.fprocess.SlopeProcess(key="m", target_column=self.macd_column_column, window=slope_window)
            signal_slope = fc.fprocess.SlopeProcess(key="s", target_column=self.macd_signal_column, window=slope_window)
            self.slope_macd_column = macd_slope.KEY_SLOPE
            self.slope_signal_column = signal_slope.KEY_SLOPE
            indicaters.extend([macd_slope, signal_slope])
        else:
            self.slope_macd_column = None
            self.slope_signal_column = None

        self.add_indicaters(indicaters)
        self.range_function = range_function

    def get_signal(self, df: pd.DataFrame, position: Position = None, symbol: str = None):
        if self.slope_signal_column is not None:
            signal = strategy.macd_renko_with_slope(
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
        else:
            signal = strategy.macd_renko(
                position,
                df,
                self.renko_bnum_column,
                self.macd_column_column,
                self.macd_signal_column,
                self.close_column_name,
                threshold=self.threshold,
            )
        if signal is not None:
            signal.volume = self.volume
            signal.symbol = symbol
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
        finance_client: fc.ClientBase,
        renko_process: fc.fprocess.RenkoProcess,
        macd_process: fc.fprocess.MACDProcess,
        bolinger_process: fc.fprocess.BBANDProcess,
        slope_window=5,
        volume=1,
        use_tp=False,
        interval_mins: int = -1,
        data_length=250,
        trailing_stop=None,
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
            volume (int, optional): The volume for the trade signals. Defaults to 1.
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
            volume=volume,
            data_length=data_length,
            trailing_stop=trailing_stop,
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

    def get_signal(self, df: pd.DataFrame, position: Position = None, symbol: str = None):
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
        if signal is not None:
            signal.volume = self.volume
            signal.symbol = symbol
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

    def __init__(self, finance_client: fc.ClientBase, cci_process=None, interval_mins: int = 30, data_length=100, volume=1, trailing_stop=None, logger=None) -> None:
        """Raise Buy/Sell signal when CCI cross up/down 0

        Args:
            finance_client (fc.Client): any finance_client
            cci_process (ProcessBase, optional): you can provide CCIProcess. Defaults to None and CCIProcess with default parameter is used.
            interval_mins (int, optional): interval minutes to get_signal this strategy. Defaults to 30.
            volume (int, optional): volume per trade. Defaults to 1.
            data_length (int, optional): data length to caliculate CCI. Defaults to 100.
            logger (Logger, optional): you can specify your logger. Defaults to None.

        Raises:
            Exception: when other than CCI process is provided.
        """
        super().__init__(finance_client=finance_client, idc_processes=None, interval_mins=interval_mins, volume=volume,
                         data_length=data_length, trailing_stop=trailing_stop, logger=logger)
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
            self.trend = Trend(TREND_TYPE.up)
        else:
            self.trend = Trend(TREND_TYPE.down)
        self.add_indicaters(indicaters)

    def get_signal(self, df: pd.DataFrame, position: Position = None, symbol: str = None):
        signal = strategy.cci_cross(position, df, self.cci_column_name, self.close_column_name)
        if signal is not None:
            signal.volume = self.volume
            signal.symbol = symbol
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
        self, finance_client: fc.ClientBase, cci_process=None, upper=100, lower=-100, interval_mins: int = 30, volume=1, data_length=100, trailing_stop=None, logger=None
    ) -> None:
        """Raise Buy/Sell signal when CCI cross up/down uppser/lower

        Args:
            finance_client (fc.Client): any finance_client
            cci_process (ProcessBase, optional): you can provide CCIProcess. Defaults to None and CCIProcess with default parameter is used.
            upper (int, option): upper value to raise Buy Signal. Defaults to 100
            lower (int, option): lower value to raise Sell Signal. Defaults to -100
            volume (int, optional): volume per trade. Defaults to 1.
            interval_mins (int, optional): interval minutes to get_signal this strategy. Defaults to 30.
            data_length (int, optional): data length to caliculate CCI. Defaults to 100.
            logger (Logger, optional): you can specify your logger. Defaults to None.

        Raises:
            Exception: when other than CCI process is provided.
            ValueException: when lower >= upper
        """
        super().__init__(finance_client=finance_client, idc_processes=None, 
                         interval_mins=interval_mins, volume=volume, data_length=data_length,
                         trailing_stop=trailing_stop, logger=logger)
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
            self.trend = Trend(TREND_TYPE.up)
        elif current_cci <= lower:
            self.trend = Trend(TREND_TYPE.down)
        else:
            self.trend = Trend(TREND_TYPE.unknown)
        self.add_indicaters(indicaters)

    def get_signal(self, df: pd.DataFrame, position: Position = None, symbol: str = None):
        signal = strategy.cci_boader(position, df, self.cci_column_name, self.close_column_name, self.upper, self.lower)
        if signal is not None:
            signal.volume = self.volume
            signal.symbol = symbol
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
        finance_client: fc.ClientBase,
        range_process=None,
        alpha=1,
        slope_ratio=0.4,
        interval_mins: int = -1,
        volume=1,
        data_length: int = 100,
        trailing_stop=None,
        logger=None,
    ) -> None:
        super().__init__(finance_client=finance_client, idc_processes=None, 
                         interval_mins=interval_mins, volume=volume, data_length=data_length,
                         trailing_stop=trailing_stop, logger=logger)
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

    def get_signal(self, df: pd.DataFrame, position: Position = None, symbol: str = None):
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
        if signal is not None:
            signal.volume = self.volume
            signal.symbol = symbol
        return signal


class MACDRenkoRange(StrategyClient):
    key = "macd_renko_range"

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
        finance_client: fc.ClientBase,
        renko_process: fc.fprocess.RenkoProcess,
        macd_process: fc.fprocess.MACDProcess,
        range_process: fc.fprocess.RangeTrendProcess,
        bolinger_process=None,
        slope_window=5,
        alpha=2,
        volume=1,
        interval_mins: int = -1,
        data_length=250,
        threshold=2,
        trailing_stop=None,
        logger=None,
    ) -> None:
        super().__init__(finance_client=finance_client, idc_processes=None, 
                         interval_mins=interval_mins, volume=volume, data_length=data_length,
                         trailing_stop=trailing_stop, logger=logger)

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

    def get_signal(self, df: pd.DataFrame, position: Position = None, symbol: str = None):
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
        if signal is not None:
            signal.volume = self.volume
            signal.symbol = symbol
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
        finance_client: fc.ClientBase,
        renko_process: fc.fprocess.RenkoProcess,
        macd_process: fc.fprocess.MACDProcess,
        bolinger_process: fc.fprocess.BBANDProcess,
        range_process=None,
        slope_window=5,
        alpha=2,
        volume=1,
        use_tp=False,
        interval_mins: int = -1,
        data_length=250,
        bolinger_threshold=None,
        rsi_column=None,
        rsi_threshold=None,
        threshold=2,
        trailing_stop=None,
        logger=None,
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
            volume=volume,
            interval_mins=interval_mins,
            data_length=data_length,
            threshold=threshold,
            trailing_stop=trailing_stop,
            logger=logger,
        )

        self.use_tp = use_tp
        self.column_dict = self.client.get_ohlc_columns()
        self.__is_in_range = False

    def get_signal(self, df: pd.DataFrame, position: Position = None, symbol: str = None):
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
        if signal is not None:
            signal.volume = self.volume
            signal.symbol = symbol
        return signal


class CascadeStrategyClient(StrategyClient):
    key = "cascade_strategy"

    def __init__(self, strategies: Union[List[StrategyClient], StrategyClient], cascade_frames: Union[List[int], Union[str]],
                 finance_client, close_condition:str = "any",
                 interval_mins=-1, volume=1, data_length=100, trailing_stop=None, save_signal_info=False) -> None:
        """ run strategy based on cascade_frames. If all strategy rise the same open signal, return the signal.


        Args:
            strategies (Union[List[StrategyClient], StrategyClient]): list of strategies to be cascaded or a single strategy
            cascade_frames (Union[List[int], Union[str]]): list of frames corresponding to the strategies. You can specify frame string like "30min", "1h"
            close_condition (str): condition to close position when multiple close signals are returned. any, all, first or last. Defaults to "any".
            interval_mins (int, optional):  interval mins to get data. Defaults to -1.
            volume (int, optional): volume per trade. Defaults to 1.
            data_length (int, optional): length of data to be used. Defaults to 100.
            trailing_stop (_type_, optional): trailing stop value. Defaults to None.
            save_signal_info (bool, optional): whether to save signal information. Defaults to False.
        """
        
        if not isinstance(strategies, list):
            strategies = [strategies]
        self.strategies = strategies

        cascade_frames_int = []
        for frame in cascade_frames:
            if isinstance(frame, str):
                frame_min = utils.to_freq(frame)
                cascade_frames_int.append(frame_min)
            else:
                cascade_frames_int.append(frame)
        if close_condition not in ["any", "all", "first", "last"]:
            raise ValueError("close_condition should be 'any', 'all', 'first' or 'last'")
        self.close_if_any = close_condition == "any"
        self.close_condition = close_condition
        # sort frames in descending order
        # cascade_frames_int.sort(reverse=True)
        self.cascade_frames = cascade_frames_int
        super().__init__(finance_client=finance_client, idc_processes=None, interval_mins=interval_mins, data_length=data_length,
                         volume=volume, trailing_stop=trailing_stop, save_signal_info=save_signal_info)
    
    def _reset_auto_index(self, org_auto_index):
        for strategy, auto_index in zip(self.strategies, org_auto_index):
            strategy.client.auto_index = auto_index

    def get_signal(self, df: pd.DataFrame, position: Position = None, symbol: str = None):
        pre_signal = None
        last_signal = None
        start_index = 0
        org_auto_index = [strategy.client.auto_index for strategy in self.strategies]
        end_index = len(self.strategies)
        if self.close_condition == "first":
            frame = self.cascade_frames[0]
            strategy = self.strategies[0]
            strategy.client.auto_index = False
            temp_df = strategy.client.get_ohlc(symbols=symbol, length=self.data_length, frame=frame, idc_processes=strategy._idc_processes)
            pre_signal = strategy.get_signal(temp_df, position=position, symbol=symbol)
            if pre_signal is not None and pre_signal.is_close:
                if pre_signal.is_buy is None:
                    self._reset_auto_index(org_auto_index)
                    return pre_signal
                else:
                    for strategy, frame in zip(self.strategies[1:], self.cascade_frames[1:]):
                        temp_df = strategy.client.get_ohlc(symbols=symbol, length=self.data_length, frame=frame, idc_processes=strategy._idc_processes)
                        strategy_signal = strategy.get_signal(temp_df, position=position, symbol=symbol)
                        if strategy_signal is None:
                            self._reset_auto_index(org_auto_index)
                            return CloseSignal(pre_signal.std_name, confidence=pre_signal.confidence, symbol=pre_signal.symbol)
                        elif pre_signal.is_buy is strategy_signal.is_buy:
                            continue
                        else:
                            self._reset_auto_index(org_auto_index)
                            return CloseSignal(pre_signal.std_name, confidence=pre_signal.confidence, symbol=pre_signal.symbol)
                    self._reset_auto_index(org_auto_index)
                    return pre_signal
            start_index = 1
        elif self.close_condition == "last":
            frame = self.cascade_frames[-1]
            strategy = self.strategies[-1]
            strategy.client.auto_index = False
            temp_df = strategy.client.get_ohlc(symbols=symbol, length=self.data_length, frame=frame, idc_processes=strategy._idc_processes)
            last_signal = strategy.get_signal(temp_df, position=position, symbol=symbol)
            if last_signal is not None and last_signal.is_close:
                self._reset_auto_index(org_auto_index)
                return last_signal
            end_index -= 1
        for strategy, frame in zip(self.strategies[start_index:end_index], self.cascade_frames[start_index:end_index]):
            temp_df = strategy.client.get_ohlc(symbols=symbol, length=self.data_length, frame=frame, idc_processes=strategy._idc_processes)
            strategy_signal = strategy.get_signal(temp_df, position=position, symbol=symbol)
            if strategy_signal is None:
                self._reset_auto_index(org_auto_index)
                return None
            elif strategy_signal.is_close and self.close_if_any:
                self._reset_auto_index(org_auto_index)
                return strategy_signal
            elif pre_signal is None:
                pre_signal = strategy_signal
            else:
                if pre_signal.is_buy is strategy_signal.is_buy:
                    pre_signal = strategy_signal
                else:
                    self._reset_auto_index(org_auto_index)
                    return None
        if last_signal is not None:
            if pre_signal.is_buy is last_signal.is_buy:
                self._reset_auto_index(org_auto_index)
                return last_signal
            else:
                self._reset_auto_index(org_auto_index)
                return None
        self._reset_auto_index(org_auto_index)
        if pre_signal is not None:
            pre_signal.volume = self.volume
            pre_signal.symbol = symbol
        return pre_signal

class Momentum(StrategyClient):
    key = "atrsma"

    def __init__(
        self,
        finance_client: fc.ClientBase,
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
        volume=1,
        data_length: int = 100,
        save_signal_info=False,
        trailing_stop=None,
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
        super().__init__(finance_client=finance_client, idc_processes=idc_processes, 
                         interval_mins=interval_mins, volume=volume, data_length=data_length,
                         save_signal_info=save_signal_info, trailing_stop=trailing_stop, logger=logger)

    def get_signal(self, df, positions: list[Position] = None, symbols: List[str] = None):
        signals = strategy.momentum_ma(
            positions,
            df,
            self.volume,
            self.momentum_column,
            self.short_ma_column,
            self.atr_column,
            self.order_price_column,
            self.baseline_column,
            self.baseline_ma_column,
            self.threshold,
            self.risk_factor,
        )
        if signals is not None:
            for signal in signals:
                signal.volume = self.volume
                signal.symbol = symbols
        return signals