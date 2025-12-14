import json
import os
from turtle import position
from typing import Union

from finance_client.client_base import ClientBase
from finance_client.position import Position

from ..signal import Signal, Trend
from logging import getLogger, config


class StrategyClient:
    key = "base"
    client: ClientBase = None

    def __init__(
        self,
        finance_client: ClientBase,
        idc_processes=...,
        interval_mins: int = None,
        amount=1,
        data_length: int = 100,
        trailing_stop=None,
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
        if not isinstance(idc_processes, list):
            idc_processes = []
        self.__idc_processes = idc_processes
        self.save_signal_info = save_signal_info
        self.amount = amount
        self.client = finance_client
        self.data_length = data_length
        self.trailing_stop = trailing_stop
        self.market_trends = {}
        if interval_mins is None:
            self.interval_mins = self.client.frame
        else:
            self.interval_mins = interval_mins

    def add_indicaters(self, idc_processes: list):
        for process in idc_processes:
            if process not in self.__idc_processes:
                self.__idc_processes.append(process)
            else:
                self.logger.info(f"{process.kinds} is already added")

    def save_signal(self, signal, data):
        # time, signal info, data
        pass

    def set_market_trend(self, symbol:str, market_trend: Trend):
        self.market_trends[symbol] = market_trend

    def get_signal(self, df, position: Position = None, symbols=...) -> Signal:
        print("please overwrite this method on an actual client.")
        return None
    
    def update_stop(self, df, positions) -> Signal:
        if self.trailing_stop is not None:
            new_stops = self.trailing_stop(df, positions)
            for id, stop_price in new_stops.items():
                self.client.update_position(position=id, sl=stop_price)
        return None

    def run(self, symbols: Union[str, list]) -> Signal:
        """run this strategy

        Args:
            symbols (Union[str, list]): symbols to run this strategy

        Returns:
            Signal: Signal of this strategy
        """
        try:
            df = self.client.get_ohlc(symbols=symbols, length=self.data_length, idc_processes=self.__idc_processes)
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

        positions = self.client.get_positions(symbols=symbols)
        self.update_stop(df, positions=positions)
        if len(positions) > 1:
            self.logger.debug(f"current positions: {[str(p) for p in positions]}")

        for symbol in symbols:
            ohlc_df = get_dataframe(df, symbol)
            if ohlc_df.empty:
                print("ohlc_df is empty. skipping...", symbol)
                continue
            if ohlc_df.iloc[-1].isnull().any() is True:
                print("last index has null. try to run anyway.", ohlc_df.iloc[-1])
            symbol_positions = [pos for pos in positions if pos.symbol == symbol]
            if len(symbol_positions) == 0:
                signal = self.get_signal(ohlc_df, None, symbol)
                if signal is not None:
                    signal.amount = self.amount
                    signal.symbol = symbol
                    signals.append(signal)
                    if self.save_signal_info:
                        self.save_signal(signal, ohlc_df)
            else:
                for position in symbol_positions:
                    signal = self.get_signal(ohlc_df, position, symbol)
                    if signal is not None:
                        signal.amount = self.amount
                        signal.symbol = symbol
                        signals.append(signal)
                        if self.save_signal_info:
                            self.save_signal(signal, ohlc_df)
        return signals


class MultiSymbolStrategyClient(StrategyClient):
    def __init__(
        self,
        finance_client: ClientBase,
        idc_processes=[],
        interval_mins: int = -1,
        amount=1,
        data_length: int = 100,
        save_signal_info=False,
        logger=None,
    ) -> None:
        super().__init__(finance_client, idc_processes, interval_mins, amount, data_length, save_signal_info, logger)

    def get_signal(self, df, position = None, symbols=None):
        if symbols is None:
            symbols = []
        return self.get_signals(df, [position], symbols)

    def get_signals(self, df, positions, symbols=None):
        if symbols is None:
            symbols = []
        if positions is None:
            positions = [0 for _ in range(len(symbols))]

        print("please overwrite this method on an actual client.")

    def run(self, symbols: Union[str, list], positions=None) -> Signal:
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

        positions = self.client.get_positions(symbols=symbols) if positions is None else positions

        signals = self.get_signals(df, positions, symbols)
        for signal in signals:
            if signal is not None:
                signals.append(signal)
                if self.save_signal_info:
                    self.save_signal(signal, df)

        return signals
