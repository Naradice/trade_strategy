import csv
import datetime
from logging import getLogger, config
import json
import os
import statistics
import threading
import time

from .strategies import StrategyClient

logger = getLogger(__name__)

class StrategyRunner:

    def __init__(self, symbols, pipeline=None) -> None:
        self.pipeline = pipeline
        self.symbols = symbols
        self.results = {symbol: [] for symbol in symbols} if symbols is not None else {}

    def get_signals(self, strategy: StrategyClient):
        if self.pipeline:
            self.pipeline.before_signal(strategy, self.symbols)
        signals = strategy.run(self.symbols)
        if self.pipeline:
            signals = self.pipeline.after_signal(signals)

        return signals
    
    def handle_signals(self, strategy: StrategyClient, signals: list):
        for index, signal in enumerate(signals):
            if signal and signal.order_type is not None:
                if signal.is_close:
                    logger.info(f"close signal is risen: {signal}")
                    results = []
                    if signal.is_buy is None:
                        results = strategy.client.close_all_positions(signal.symbol)
                        if results:
                            logger.info(f"positions are closed, remaining budget is {strategy.client.account.get_free_margin()}")
                    elif signal.is_buy is True:
                        results = strategy.client.close_short_positions(signal.symbol)
                        if results:
                            logger.info(f"short positions are closed, remaining budget is {strategy.client.account.get_free_margin()}")
                    elif signal.is_buy is False:
                        results = strategy.client.close_long_positions(signal.symbol)
                        if results:
                            logger.info(f"long positions are closed, remaining budget is {strategy.client.account.get_free_margin()}")
                    if len(results) > 0:
                        for result in results:
                            # (price, position.price, price_diff, profit, True)
                            if result is not None:
                                if result.error:
                                    logger.info(f"pending closed result: {result}")
                                    self.results[signal.symbol].append(result.profit)
                                else:
                                    logger.info(f"closed result: {result}")
                                    self.results[signal.symbol].append(result.profit)
                if signal.id != 10:
                    if signal.is_buy:
                        position = strategy.client.open_trade(
                            signal.is_buy,
                            volume=signal.volume,
                            price=signal.order_price,
                            tp=signal.tp,
                            sl=signal.sl,
                            order_type=signal.order_type,
                            symbol=signal.symbol,
                        )
                        logger.info(
                            f"long position is opened: {str(position)} based on {signal}, remaining budget is {strategy.client.account.get_free_margin()}"
                        )
                    elif signal.is_buy is False:
                        position = strategy.client.open_trade(
                            is_buy=signal.is_buy,
                            volume=signal.volume,
                            price=signal.order_price,
                            tp=signal.tp,
                            sl=signal.sl,
                            order_type=signal.order_type,
                            symbol=signal.symbol,
                        )
                        logger.info(
                            f"short position is opened: {str(position)} based on {signal}, remaining budget is {strategy.client.account.get_free_margin()}"
                        )



class ParallelStrategyManager:
    def __init__(self, strategies: list, days=0, hours=0, minutes=0, seconds=0, pipeline=None, logger=None, symbols=None, result_csv_path=None) -> None:
        self.event = threading.Event()
        self.result_csv_path = result_csv_path
        if logger is not None:
            logger.warning("logger is deprecated, use module logger instead")

        if type(strategies) == list and len(strategies) > 0:
            self.strategies = strategies
            self.__duration = datetime.timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
        self.done = False
        if isinstance(symbols, list):
            self.symbols = symbols
        elif isinstance(symbols, str):
            self.symbols = [symbols]
        elif symbols is None:
            # calculate union of symbols from all strategies
            self.symbols = list(set().union(*[strategy.client.symbols for strategy in strategies]))
        else:
            raise TypeError(f"symbols should be list or str, but got {type(symbols)}")
        self.runner = StrategyRunner(self.symbols, pipeline=pipeline)

    def _sleep_until_frame_time(self, interval_mins: int):
        if interval_mins > 0:
            base_time = datetime.datetime.now()
            target_min = datetime.timedelta(minutes=(interval_mins - base_time.minute % interval_mins))
            target_time = base_time + target_min
            sleep_time = datetime.datetime.timestamp(target_time) - datetime.datetime.timestamp(base_time) - base_time.second
            if sleep_time > 0:
                logger.debug(f"wait {sleep_time} to start on frame time")
                time.sleep(sleep_time)

    def _get_signals(self, strategy: StrategyClient):
        if self.pipeline:
            self.pipeline.before_signal(strategy, self.symbols)
        signals = strategy.run(self.symbols)
        if self.pipeline:
            signals = self.pipeline.after_signal(signals)

        return signals

    def _start_strategy(self, strategy: StrategyClient):
        interval_mins = strategy.interval_mins
        self._sleep_until_frame_time(interval_mins)

        if interval_mins > 0:
            interval = interval_mins * 60
            do_sleep = True
        else:
            interval = 1
            do_sleep = False

        count = 0
        if self.symbols is None:
            self.symbols = strategy.client.symbols.copy()

        while datetime.datetime.now() < self.__end_time and self.done is False:
            start_time = datetime.datetime.now()
            try:
                signals = self.runner.get_signals(strategy)
            except StopIteration:
                logger.info("CSV data exhausted, ending strategy")
                break
            end_time = datetime.datetime.now()
            diff = end_time - start_time
            logger.debug(f"took {diff} for caliculate the signal")
            self.runner.handle_signals(strategy, signals)
            if do_sleep:
                base_time = time.time()
                next_time = ((base_time - time.time()) % interval) or interval
                logger.debug(f"wait {next_time} to run on next frame")
                if self.event.wait(timeout=next_time):
                    # logger.info("Close all positions as for ending the strategies.")
                    # strategy.client.close_all_positions()
                    break
                self.event.clear()
            if count % 10 == 0:
                try:
                    print(strategy.client.get_portfolio())
                    print(strategy.client.get_free_margin())
                except Exception as e:
                    logger.error(f"error occured when getting portfolio or budget: {e}")
            count += 1

        for symbol, results in self.runner.results.items():
            totalSignalCount = len(results)
            if totalSignalCount != 0:
                revenue = sum(results)
                winList = list(filter(lambda x: x >= 0, results))
                winCount = len(winList)
                winRevenue = sum(winList)
                resultTxt = f"{symbol}, Revenue:{revenue}, signal count: {totalSignalCount}, win Rate: {winCount/totalSignalCount}, plus: {winRevenue}, minus: {revenue - winRevenue}"
                logger.info(resultTxt)
                var = statistics.pvariance(results)
                mean = statistics.mean(results)
                logger.info(f"strategy assessment: revenue mean: {mean}, var: {var}")
                if self.result_csv_path is not None:
                    try:
                        with open(self.result_csv_path, mode="a", newline="") as f:
                            writer = csv.writer(f)
                            writer.writerow([symbol, revenue, totalSignalCount, winCount, winRevenue, mean, var])
                    except Exception as e:
                        logger.error(f"error occured when writing result csv: {e}")
        print(f"Strategy Ended. Frame: {strategy.client.frame}")

    def start_strategies(self, wait=True):
        self.__start_time = datetime.datetime.now()
        self.__end_time = self.__start_time + self.__duration
        self.done = False

        for strategy in self.strategies:
            if strategy.client.do_render:
                try:
                    self._start_strategy(strategy)
                except KeyboardInterrupt:
                    logger.info("Finish the strategies as KeyboardInterrupt happened")
                    self.summary()
                    self.event.set()
                    self.done = True
                    exit()
            else:
                t = threading.Thread(target=self._start_strategy, args=(strategy,), daemon=False)
                t.start()
                logger.debug("started strategy")
                if wait:
                    try:
                        ui = input("Please input 'exit' to end the strategies.")
                        if ui.lower() == "exit":
                            self.event.set()
                            self.done = True
                            if t.is_alive():
                                try:
                                    exit()
                                except Exception:
                                    pass
                    except KeyboardInterrupt:
                        logger.info("Finish the strategies as KeyboardInterrupt happened")
                        self.event.set()
                        self.done = True
                        if t.is_alive():
                            try:
                                exit()
                            except Exception:
                                pass

    def stop_strategies(self):
        self.done = True

    def summary(self):
        totalRevenue = 0
        totalWinCount = 0
        totalSignalCount = 0
        totalWinRevenute = 0
        for strategy in self.strategies:
            symbol = strategy.client.symbols[0]
            totalRevenue += sum(self.results[symbol])
            totalSignalCount += len(self.results[symbol])
            winList = list(filter(lambda x: x >= 0, self.results[symbol]))
            totalWinCount += len(winList)
            totalWinRevenute = sum(winList)
        resultTxt = f"Revenute:{totalRevenue}, signal count: {totalSignalCount}, win Rate: {totalWinCount}, plus: {totalWinRevenute}, minus: {totalRevenue - totalWinRevenute}"
        print(resultTxt)