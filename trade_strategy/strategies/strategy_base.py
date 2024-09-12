import json
import os

import finance_client as fc

from ..signal import Signal
from logging import getLogger, config


class StrategyClient:
    key = "base"
    client: fc.Client = None

    def __init__(
        self,
        financre_client: fc.Client,
        idc_processes=...,
        interval_mins: int = None,
        amount=1,
        data_length: int = 100,
        save_signal_info=False,
        logger=None,
    ) -> None:
        if logger is None:
            try:
                with open(os.path.abspath(os.path.join(os.path.dirname(__file__), "../settings.json")), "r") as f:
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

        if hasattr(idc_processes, "len"):
            self._idc_processes = idc_processes
        else:
            self._idc_processes = None
        self.save_signal_info = save_signal_info
        self.amount = amount
        self.client = financre_client
        self.data_length = data_length
        if interval_mins is None:
            self.interval_mins = self.client.frame
        else:
            self.interval_mins = interval_mins
        self.trend = {}  # 0 don't have, 1 have long_position, -1 short_position

    def add_indicaters(self, idc_processes: list):
        for process in idc_processes:
            if process not in self._idc_processes:
                self._idc_processes.append(process)
            else:
                self.logger.info(f"{process.kinds} is already added")

    def save_signal(self, signal, data):
        # time, signal info, data
        pass

    def update_trend(self, signal: Signal):
        if signal is not None:
            self.trend[signal.symbol] = signal.trend

    def get_signal(self, df, position: int = None, symbols=...) -> Signal:
        self.logger.debug("please overwrite this method on an actual client.")
        return None

    def get_observation(self, symbols):
        try:
            df = self.client.get_ohlc(self.data_length, symbols, idc_processes=self._idc_processes)
            return df
        except Exception as e:
            self.logger.error(f"error occured when client gets ohlc data: {e}")
            self.logger.debug(f"{self.data_length}, {symbols}, {self._idc_processes}")
        return []

    def run(self, symbols: str or list, position=None) -> Signal:
        """run this strategy

        Args:
            position (int, optional): represents the trend. When manually or other strategy buy/sell, you can pass 1/-1 to this strategy. Defaults to None.

        Returns:
            Signal: Signal of this strategy
        """
        df = self.get_observation(symbols)
        signals = []
        if type(symbols) is str:
            symbols = [symbols]
        if len(symbols) == 1:
            get_dataframe = lambda df, key: df
        else:
            get_dataframe = lambda df, key: df[key]

        for symbol in symbols:
            if position is None:
                if symbol in self.trend:
                    position = self.trend[symbol].id
                else:
                    position = 0
            else:
                position = position
            self.logger.debug(f"get data for a {symbol}")
            ohlc_df = get_dataframe(df, symbol)
            signal = self.get_signal(ohlc_df, position, symbol)
            if signal is not None:
                signal.amount = self.amount
                signal.symbol = symbol
                self.update_trend(signal)
                signals.append(signal)
                if self.save_signal_info:
                    self.save_signal(signal, ohlc_df)

        return signals


class MultiSymbolStrategyClient(StrategyClient):
    def __init__(
        self,
        financre_client: fc.Client,
        idc_processes=...,
        interval_mins: int = -1,
        amount=1,
        data_length: int = 100,
        save_signal_info=False,
        logger=None,
    ) -> None:
        super().__init__(financre_client, idc_processes, interval_mins, amount, data_length, save_signal_info, logger)

    def get_signal(self, df, position: int = None, symbols=None):
        if symbols is None:
            symbols = []
        return self.get_signals(df, [position], symbols)

    def get_signals(self, df, positions, symbols=None):
        if symbols is None:
            symbols = []
        if positions is None:
            positions = [0 for _ in range(len(symbols))]

        print("please overwrite this method on an actual client.")

    def run(self, symbols: str or list, positions=None) -> Signal:
        """run this strategy

        Args:
            positions (list[int], optional): represents the trend. When manually or other strategy buy/sell, you can pass 1/-1 to this strategy. Defaults to None.

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

        if positions is None:
            positions = []
            for symbol in symbols:
                if symbol in self.trend:
                    positions.append(self.trend[symbol].id)
                else:
                    positions.append(0)

        signals = self.get_signals(df, positions, symbols)
        for signal in signals:
            if signal is not None:
                self.update_trend(signal)
                signals.append(signal)
                if self.save_signal_info:
                    self.save_signal(signal, df)

        return signals
