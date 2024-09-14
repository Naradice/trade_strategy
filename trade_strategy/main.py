import datetime
import multiprocessing
import signal
import statistics
import threading
import time
from logging import INFO
from typing import Any

import pandas as pd
from trade_strategy.strategies import StrategyClient

from .strategies import StrategyClient
from .console import Console, Command, initialize_logger


class Timer:
    def __init__(self, start_date: datetime.datetime, end_date: datetime.datetime, logger) -> None:
        self.start_date = start_date
        self.end_date = end_date
        self.done = False
        self.is_timer_running = False
        self.logger = logger

    def _sleep(self, secs: float):
        if secs < 0:
            return None
        sleep_unit = 10
        sleep_counts = secs // sleep_unit
        sleep_sec = secs % sleep_unit
        time.sleep(sleep_sec)
        while sleep_counts > 0 and self.done is False:
            time.sleep(sleep_unit)
            sleep_counts -= 1

    def _timer_sleep(self, event, pipe, update_frame):
        while datetime.datetime.now() < self.end_date and self.done is False:
            if update_frame is not None:
                self._sleep(update_frame)
                try:
                    event.set()
                except Exception as e:
                    self.logger.debug(f"failed to fire timer event: {e}")
            else:
                delta = self.end_date - datetime.datetime.now()
                self._sleep(delta.total_seconds())
        try:
            pipe.send(Command.end)
        except Exception:
            pass

    def _wait_until_start_date(self):
        delta = self.start_date - datetime.datetime.now()
        delta_seconds = delta.total_seconds()
        if delta_seconds > 0:
            if delta_seconds < 60:
                self.logger.info(f"sleep {delta_seconds} seconds")
            else:
                self.logger.info(f"sleep {delta_seconds/60} mins")
            self._sleep(delta_seconds)

    def __call__(self, timer_event, pipe, update_frame_minutes) -> Any:
        # convert minutes to seconds
        if update_frame_minutes is None:
            update_frame = None
        elif update_frame_minutes < 0:
            update_frame = update_frame_minutes
        else:
            update_frame = update_frame_minutes * 60
        if self.is_timer_running is False:
            t = threading.Thread(target=self._wait_until_start_date, daemon=False)
            t.start()
            t.join()
            t = threading.Thread(target=self._timer_sleep, args=(timer_event, pipe, update_frame), daemon=False)
            t.start()
            self.is_timer_running = True

    def sleep(self, seconds):
        try:
            self._sleep(seconds)
        except KeyboardInterrupt:
            pass


class ParallelTimer(Timer):
    def __init__(self, start_date: datetime, end_date: datetime, logger) -> None:
        super().__init__(start_date, end_date, logger)

    def _timer_sleep(self, time_pipe, command_pipe, update_frame_df: pd.DataFrame):
        initial_freq = dict(update_frame_df.reset_index().values)

        while datetime.datetime.now() < self.end_date and self.done is False:
            update_frame_df.sort_values(by="freq", inplace=True)
            popped_freq_df = update_frame_df.iloc[0]
            update_frame_df = update_frame_df.iloc[1:]

            sleep_mins = popped_freq_df["freq"]
            popped_index = popped_freq_df.name
            update_frame_df -= sleep_mins
            initial_sleep_mins = initial_freq[popped_index]
            popped_initial_time_df = pd.DataFrame({"freq": [initial_sleep_mins]}, index=[popped_index])
            self._sleep(sleep_mins * 60)
            try:
                time_pipe.send(popped_index)
            except Exception:
                pass
            update_frame_df = pd.concat([update_frame_df, popped_initial_time_df])
        try:
            command_pipe.send(Command.end)
        except Exception:
            pass

    def __call__(self, timer_pipe, pipe, update_frame_minutes_list: list) -> Any:
        # check if length greater than or equal to 2
        if len(update_frame_minutes_list) < 2:
            raise ValueError("length is less than 1. Please use Timer")
        # if one of them is less than 0, return error
        for frame in update_frame_minutes_list:
            if frame < 0:
                raise ValueError("simulation time frame is not suppported.")
        # if all of them are greater than 0, run timer
        if self.is_timer_running is False:
            indices = list(range(len(update_frame_minutes_list)))
            update_frame_df = pd.DataFrame({"freq": update_frame_minutes_list}, index=indices)

            t = threading.Thread(target=self._wait_until_start_date, daemon=False)
            t.start()
            t.join()
            t = threading.Thread(target=self._timer_sleep, args=(timer_pipe, pipe, update_frame_df), daemon=False)
            t.start()
            self.is_timer_running = True


class StrategyManager:
    def __init__(self, start_date, end_date, logger=None, log_level=INFO, console_mode=True) -> None:
        if console_mode:
            self.logger = Console(logger=logger, log_level=log_level)
        else:
            self.logger = initialize_logger(logger, log_level=log_level)
        self.stop_event = threading.Event()
        self.timer = Timer(start_date=start_date, end_date=end_date, logger=self.logger)
        self.enable_long = True
        self.enable_short = True

    def _summary(self, results: dict):
        for symbol, values in results.items():
            totalSignalCount = len(values)
            if totalSignalCount > 0:
                revenue = sum(values)
                winList = list(filter(lambda x: x >= 0, values))
                winCount = len(winList)
                winRevenute = sum(winList)
                self.logger.info(
                    f"{symbol}, Revenute:{revenue}, signal count: {totalSignalCount}, win Rate: {winCount/totalSignalCount}, plus: {winRevenute}, minus: {revenue - winRevenute}, revenue ratio: {winRevenute/revenue}"
                )
                var = statistics.pvariance(values)
                mean = statistics.mean(values)
                self.logger.info(f"strategy assesment: revenue mean: {mean}, var: {var}")

    def _handle_signal(self, strategy, signal):
        if signal and signal.order_type is not None:
            position = None
            close_results = []
            if signal.is_close:
                self.logger.info(f"close signal is risen: {signal}")
                if signal.is_buy is None:
                    close_results = strategy.client.close_all_positions(signal.symbol)
                    if close_results:
                        self.logger.info(f"positions are closed, remaining budget is {strategy.client.wallet.budget}")
                elif signal.is_buy is True:
                    close_results = strategy.client.close_short_positions(signal.symbol)
                    if close_results:
                        self.logger.info(f"short positions are closed, remaining budget is {strategy.client.wallet.budget}")
                elif signal.is_buy is False:
                    close_results = strategy.client.close_long_positions(signal.symbol)
                    if close_results:
                        self.logger.info(f"long positions are closed, remaining budget is {strategy.client.wallet.budget}")
            # if signal is close_buy/sell, buy operation should be handled after close
            if signal.id != 10:
                if signal.is_buy:
                    position = strategy.client.open_trade(
                        signal.is_buy,
                        amount=signal.amount,
                        price=signal.order_price,
                        tp=signal.tp,
                        sl=signal.sl,
                        order_type=signal.order_type,
                        symbol=signal.symbol,
                    )
                    self.logger.info(
                        f"long position is opened: {str(position)} based on {signal}, remaining budget is {strategy.client.wallet.budget}"
                    )
                elif signal.is_buy is False:
                    position = strategy.client.open_trade(
                        is_buy=signal.is_buy,
                        amount=signal.amount,
                        price=signal.order_price,
                        tp=signal.tp,
                        sl=signal.sl,
                        order_type=signal.order_type,
                        symbol=signal.symbol,
                    )
                    self.logger.info(
                        f"short position is opened: {str(position)} based on {signal}, remaining budget is {strategy.client.wallet.budget}"
                    )
            return position, close_results
        return None, []

    def _start_strategy(self, strategy: StrategyClient, count=-1):
        self.logger.debug("started strategy")
        results = {}
        symbols = strategy.client.symbols.copy()
        for symbol in symbols:
            results[symbol] = []

        if self.stop_event.is_set() is False:
            symbols = strategy.client.symbols.copy()
            start_time = datetime.datetime.now()
            try:
                signals = strategy.run(symbols)
            except Exception as e:
                self.logger.error(f"error happened when get signals: {e}")
                self.logger.info("stop strategy since an error happened when get signals")
                self.end()
                return None
            end_time = datetime.datetime.now()
            diff = end_time - start_time
            self.logger.debug(f"took {diff} for caliculate the signal")
            for signal in signals:
                position, closed_results = self._handle_signal(strategy, signal)
                for result in closed_results:
                    # (price, position.price, price_diff, profit, True)
                    if result is not None:
                        if result[-1]:
                            self.logger.info(f"closed result: {result}")
                            results[symbol].append(result[2])
                        else:
                            self.logger.info(f"pending closed result: {result}")
                            results[symbol].append(result[0][2])
            if count % 10 == 0:
                self.logger.info(strategy.client.get_portfolio())
                self.logger.info(strategy.client.get_budget())
            count += 1
        self._summary(results)

    def start(self, strategy: StrategyClient, wait=False):
        parent_pipe, child_pipe = multiprocessing.Pipe()
        timer_event = threading.Event()
        if hasattr(self.logger, "input"):
            self.logger.debug("start waiting user input")
            self.logger.input(child_pipe)
        self.logger.debug("start timer")
        try:
            self.timer(timer_event, child_pipe, strategy.interval_mins)
        except Exception as e:
            self.end()
            raise e

        if strategy.client.do_render:
            try:
                self._start_strategy(strategy)
            except KeyboardInterrupt:
                self.logger.info("Finish the strategies as KeyboardInterrupt happened")
                self.stop_event.set()
                exit()
        else:
            s_t = threading.Thread(target=self._on_timer_event, args=(strategy, timer_event), daemon=True)
            s_t.start()
            c_t = threading.Thread(target=self._handle_command, args=(parent_pipe,), daemon=True)
            c_t.start()

            def signal_handler(sig, frame):
                try:
                    child_pipe.send(Command.end)
                except Exception:
                    pass
                self.stop_event.set()
                self.logger.debug("strategy thred is closed")
                c_t.join()
                self.logger.debug("command thred is closed")
                self.logger.close()
                self.logger.debug("console thred is closed")
                self.timer.done = True

            signal.signal(signal.SIGINT, signal_handler)
            if wait:
                s_t.join()

    def _on_timer_event(self, strategy, timer_event: threading.Event):
        while self.stop_event.is_set() is False:
            if timer_event.wait(60):
                self._start_strategy(strategy)
                timer_event.clear()

    def _handle_command(self, pipe):
        while self.stop_event.is_set() is False:
            msg = pipe.recv()
            if msg == Command.disable:
                self.enable_long = False
                self.enable_short = False
            elif msg == Command.disable_long:
                self.enable_long = False
            elif msg == Command.disable_short:
                self.enable_short = False
            elif msg == Command.enable:
                self.enable_long = True
                self.enable_short = True
            elif msg == Command.enable_short:
                self.enable_short = True
            elif msg == Command.enable_long:
                self.enable_long = True
            elif msg == Command.end:
                self.end()
                break

    def reset(self, start_date, end_date):
        self.stop_event.set()
        self.stop_event = threading.Event()
        self.timer = Timer(start_date=start_date, end_date=end_date)
        self.enable_long = True
        self.enable_short = True

    def end(self):
        self.stop_event.set()
        if hasattr(self.logger, "close"):
            self.logger.close()
        self.timer.done = True


class ParallelStrategyManager(StrategyManager):
    def __init__(self, start_date, end_date, logger=None, log_level=INFO, console_mode=True) -> None:
        super().__init__(start_date, end_date, logger, log_level, console_mode=console_mode)
        self.timer = ParallelTimer(start_date, end_date, self.logger)

    def _on_timer_pipe(self, strategies, timer_pipe: multiprocessing.Pipe):
        while self.stop_event.is_set() is False:
            strategy_index = timer_pipe.recv()
            if strategy_index >= 0:
                if strategy_index < len(strategies):
                    t = threading.Thread(target=self._start_strategy, args=(strategies[strategy_index],), daemon=True)
                    t.start()
                else:
                    self.logger.error(f"invalid index({strategy_index}) is specified by timer event.")
            else:
                break

    def start(self, strategies: list, wait=True):
        if len(strategies) <= 1:
            raise ValueError("Length of strategy list is less than 1. Please use StrategyManager.")
        command_parent_pipe, command_child_pipe = multiprocessing.Pipe()
        timer_parent_pipe, timer_child_pipe = multiprocessing.Pipe()
        update_frame_minutes_list = [strategy.interval_mins for strategy in strategies]
        self.timer(timer_pipe=timer_child_pipe, pipe=command_child_pipe, update_frame_minutes_list=update_frame_minutes_list)
        if hasattr(self.logger, "input"):
            self.logger.input(command_child_pipe)
        warned = False

        for strategy in strategies:
            if strategy.client.do_render:
                if warned is False:
                    self.logger.warn("disable to render mode since Parallel strategy doesn't support it")
                    warned = True
                strategy.client.do_render = False
            strategy.logger = self.logger
        t = threading.Thread(target=self._on_timer_pipe, args=(strategies, timer_parent_pipe), daemon=True)
        t.start()
        c_t = threading.Thread(target=self._handle_command, args=(command_parent_pipe,), daemon=True)
        c_t.start()

        def signal_handler(sig, frame):
            try:
                command_child_pipe.send(Command.end)
                timer_child_pipe.send(-100)
            except Exception:
                pass
            self.stop_event.set()
            self.logger.debug("strategy thred is closed")
            c_t.join()
            self.logger.debug("command thred is closed")
            self.logger.close()
            self.logger.debug("console thred is closed")
            self.timer.done = True

        signal.signal(signal.SIGINT, signal_handler)
        if wait:
            t.join()
