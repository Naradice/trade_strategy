import datetime
from typing import Union, List

from .strategy_base import StrategyClient
from ..signal import Signal
from ..signal import CloseSignal


class CascadeStrategyClient:
    key = "cascade"

    def __init__(
        self,
        clients: Union[StrategyClient, List[StrategyClient], dict],
        frames: ...,
        logger=None,
    ) -> None:
        num_of_clients = 1
        try:
            num_of_clients = len(clients)
        except Exception:
            pass
        if num_of_clients > 1:
            if len(frames) != len(clients):
                raise ValueError("frames and clients should have the same length")
            if type(clients) == list:
                self.st_client = {}
                for index, frame in enumerate(frames):
                    self.st_client[frame] = clients[index]
            elif type(clients) == dict:
                self.st_client = clients
            else:
                raise TypeError("clients should be, strategy client or its list or dict")
            self.__multi_client = True
            self.__client_frame = {}
            _pre_interval = None
            for frame, client in self.st_client.items():
                self.__client_frame[frame] = client.client.frame
                if _pre_interval is None:
                    _pre_interval = client.interval_mins
                else:
                    if _pre_interval != client.interval_mins:
                        raise ValueError(f"All strategy client must have the same interval. found {_pre_interval} and {client.interval_mins}")
        else:
            self.st_client = clients
            self.__multi_client = False
            self.__client_frame = self.st_client.client.frame

        for frame in frames:
            if self.__multi_client:
                client_frame = self.__client_frame[frame]
            else:
                client_frame = self.__client_frame
            if frame < client_frame:
                raise Exception("can't specify lower than client frame.")
        self.frames = sorted(list(set(frames)), reverse=True)
        self.signals = {}
        self.last_time = {}
        for frame in self.frames:
            self.signals[frame] = None
            self.last_time[frame] = None
        if logger is None:
            if self.__multi_client:
                self.logger = self.st_client[0].logger
            else:
                self.logger = self.st_client.logger
        else:
            self.logger = logger
        self._position = 0

    def _get_signal_for_a_frame(self, df, frame, position: int = None, symbol=None) -> Signal:
        if self.__multi_client:
            client_frame = self.__client_frame[frame]
            client = self.st_client[frame]
        else:
            client_frame = self.__client_frame
            client = self.st_client

        if frame > client_frame:
            target_df = client.client.roll_ohlc_data(df, frame, **client.client.ohlc_columns, grouped_by_symbol=False)
            for process in client._idc_processes:
                target_df = process(target_df)
        else:
            target_df = df
        signal = client.get_signal(target_df, position, symbol)
        if signal is not None:
            if type(symbol) == list:
                signal.symbol = symbol[0]
            else:
                signal.symbol = symbol
            self.logger.debug(f"{signal} rose for {frame}")
        return signal

    def _check_frame_time_past(self, previouse_time: datetime.datetime, current_time: datetime.datetime, frame):
        try:
            delta = current_time - previouse_time
            delta_mins = delta.total_seconds() / 60
            self.logger.debug(f"{delta_mins} past for {frame} frame")
            if frame <= delta_mins:
                return True
            else:
                return False
        except Exception as e:
            print(f"can't calculate delta from index: {e}")
            return False

    def get_signal(self, position: int = None, symbol: str = None) -> Signal:
        parent_signal = None
        handled_frame = None
        df = None
        for index, frame in enumerate(self.frames):
            if self.__multi_client:
                client = self.st_client[frame]
            else:
                client = self.st_client

            if client.client.frame != handled_frame:
                df = client.get_observation(symbol)
                handled_frame = client.client.frame
            if self.last_time[frame] is None:
                signal = self._get_signal_for_a_frame(df, frame, position, symbol)
                self.last_time[frame] = df.index[-1]
            elif self._check_frame_time_past(self.last_time[frame], df.index[-1], frame):
                signal = self._get_signal_for_a_frame(df, frame, position, symbol)
                self.last_time[frame] = df.index[-1]
            else:
                signal = self.signals[frame]

            if signal is not None:
                if signal.is_close is True:
                    if signal.id != 10:
                        if index != 0:
                            signal = CloseSignal(signal.std_name, signal.price, signal.possibility, symbol=signal.symbol)
                            self._position = 0
                            # return None
                        else:
                            if signal.is_buy:
                                self._position = 1
                            else:
                                self._position = -1
                    else:
                        self.signals[frame] = None
                        self._position = 0
                    return signal
                if position == 0:
                    self.signals[frame] = signal
                    if index == 0:
                        parent_signal = signal
                    else:
                        if parent_signal != signal:
                            return None
                else:
                    return None
            else:
                return None
        if signal.is_buy:
            self._position = 1
        elif signal.is_buy is False:
            self._position = -1
        return signal

    def run(self, symbol: str, position=None) -> Signal:
        if position is None:
            position = self._position
        signal = self.get_signal(position, symbol)
        return [signal]

    def __getattr__(self, __name):
        if self.__multi_client:
            for frame, client in self.st_client.items():
                if hasattr(client, __name):
                    return getattr(client, __name)
        else:
            if hasattr(self.st_client, __name):
                return getattr(self.st_client, __name)
