import datetime
from logging import getLogger, config
import json
import os
import statistics
import threading
import time

from .strategies import StrategyClient


class ParallelStrategyManager:
    def __init__(self, strategies: list, days=0, hours=0, minutes=0, seconds=0, logger=None) -> None:
        self.event = threading.Event()
        if logger is None:
            dir = os.path.dirname(__file__)
            try:
                with open(os.path.join(dir, "./settings.json"), "r") as f:
                    settings = json.load(f)
            except Exception as e:
                self.logger.error(f"fail to load settings file on strategy main: {e}")
                raise e
            logger_config = settings["log"]
            try:
                config.dictConfig(logger_config)
            except Exception as e:
                self.logger.error(f"fail to set configure file on strategy main: {e}")
                raise e
            self.logger = getLogger(__name__)
        else:
            self.logger = logger
            for strategy in strategies:
                strategy.logger = logger

        self.results = {}
        if type(strategies) == list and len(strategies) > 0:
            self.strategies = strategies
            self.__duration = datetime.timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
            for strategy in strategies:
                self.results[strategy.key] = []
        self.done = False

    def __start_strategy(self, strategy: StrategyClient):
        interval_mins = strategy.interval_mins
        if interval_mins > 0:
            interval = interval_mins * 60
            do_sleep = True
        else:
            interval = 1
            do_sleep = False

        if do_sleep:
            base_time = datetime.datetime.now()
            target_min = datetime.timedelta(minutes=(interval_mins - base_time.minute % interval_mins))
            target_time = base_time + target_min
            sleep_time = datetime.datetime.timestamp(target_time) - datetime.datetime.timestamp(base_time) - base_time.second
            if sleep_time > 0:
                self.logger.debug(f"wait {sleep_time} to start on frame time")
                time.sleep(sleep_time)

        count = 0
        buySignalCount = 0
        sellSignalCount = 0
        closedCount = 0
        closedByPendingCount = 0
        symbols = strategy.client.symbols
        for symbol in symbols:
            self.results[symbol] = []

        while datetime.datetime.now() < self.__end_time and self.done is False:
            start_time = datetime.datetime.now()
            signals = strategy.run(symbols)
            end_time = datetime.datetime.now()
            diff = end_time - start_time
            self.logger.debug(f"took {diff} for caliculate the signal")
            for index, signal in enumerate(signals):
                if signal and signal.order_type is not None:
                    if signal.is_close:
                        self.logger.info(f"close signal is raised. {signal}")
                        results = []
                        if signal.is_buy is None:
                            results = strategy.client.close_all_positions(signal.symbol)
                            if results:
                                self.logger.info(f"positions are closed, remaining budget is {strategy.client.wallet.budget}")
                        elif signal.is_buy is True:
                            results = strategy.client.close_short_positions(signal.symbol)
                            if results:
                                self.logger.info(f"short positions are closed, remaining budget is {strategy.client.wallet.budget}")
                        elif signal.is_buy is False:
                            results = strategy.client.close_long_positions(signal.symbol)
                            if results:
                                self.logger.info(f"long positions are closed, remaining budget is {strategy.client.wallet.budget}")

                        if len(results) > 0:
                            for result in results:
                                # (price, position.price, price_diff, profit, True)
                                if result is not None:
                                    if result[-1]:
                                        self.logger.info(f"closed result: {result}")
                                        closedCount += 1
                                        self.results[symbol].append(result[2])
                                    else:
                                        self.logger.info(f"pending closed result: {result}")
                                        closedByPendingCount += 1
                                        self.results[symbol].append(result[0][2])
                    else:
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
                            buySignalCount += 1
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
                            sellSignalCount += 1
            if do_sleep:
                base_time = time.time()
                next_time = ((base_time - time.time()) % interval) or interval
                self.logger.debug(f"wait {sleep_time} to run on next frame")
                # time.sleep(next_time)
                if self.event.wait(timeout=next_time):
                    # self.logger.info("Close all positions as for ending the strategies.")
                    # strategy.client.close_all_positions()
                    break
            if count % 10 == 0:
                self.logger.debug(f"{count+1} times caliculated. {buySignalCount}, {sellSignalCount}, {closedCount}, {closedByPendingCount}")
                print(strategy.client.get_portfolio())
                print(strategy.client.get_budget())
            count += 1

        for symbol in symbols:
            totalSignalCount = len(self.results[symbol])
            if totalSignalCount != 0:
                revenue = sum(self.results[symbol])
                winList = list(filter(lambda x: x >= 0, self.results[symbol]))
                winCount = len(winList)
                winRevenute = sum(winList)
                resultTxt = f"{symbol}, Revenute:{revenue}, signal count: {totalSignalCount}, win Rate: {winCount/totalSignalCount}, plus: {winRevenute}, minus: {revenue - winRevenute}, revenue ratio: {winRevenute/revenue}"
                self.logger.info(resultTxt)
                self.logger.info(
                    f"buy signal raised:{buySignalCount}, sell signal raise:{sellSignalCount}, close signal is handled: {closedCount}, closed by market: {closedByPendingCount}"
                )
                var = statistics.pvariance(self.results[symbol])
                mean = statistics.mean(self.results[symbol])
                self.logger.info(f"strategy assesment: revenue mean: {mean}, var: {var}")
                # TODO: add profit per year
        print(f"Storategy Ended. Frame: {strategy.client.frame}")

    def start_strategies(self, wait=True):
        self.__start_time = datetime.datetime.now()
        self.__end_time = self.__start_time + self.__duration
        self.done = False

        for strategy in self.strategies:
            if strategy.client.do_render:
                try:
                    self.__start_strategy(strategy)
                except KeyboardInterrupt:
                    self.logger.info("Finish the strategies as KeyboardInterrupt happened")
                    self.event.set()
                    self.done = True
                    exit()
            else:
                t = threading.Thread(target=self.__start_strategy, args=(strategy,), daemon=False)
                t.start()
                self.logger.debug("started strategy")
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
                        self.logger.info("Finish the strategies as KeyboardInterrupt happened")
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
