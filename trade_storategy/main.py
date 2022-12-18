import datetime
import threading
import time
from trade_storategy.storategies import StorategyClient
from logging import getLogger, config
import json
import os

class ParallelStorategyManager:
    
    def __init__(self, storategies:list, days=0, hours=0, minutes=0, seconds=0,  logger = None) -> None:
        self.event = threading.Event()
        if logger == None:
            dir = os.path.dirname(__file__)
            try:
                with open(os.path.join(dir, './settings.json'), 'r') as f:
                    settings = json.load(f)
            except Exception as e:
                self.logger.error(f"fail to load settings file on storategy main: {e}")
                raise e
            logger_config = settings["log"]
            try:
                config.dictConfig(logger_config)
            except Exception as e:
                self.logger.error(f"fail to set configure file on storategy main: {e}")
                raise e
            self.logger = getLogger(__name__)
        else:
            self.logger = logger
            for storategy in storategies:
                storategy.logger = logger
            
        self.results = {}
        if type(storategies) == list and len(storategies) > 0:
            self.storategies = storategies
            self.__duration = datetime.timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
            for storategy in storategies:
                self.results[storategy.key] = []
        self.done = False
            
    def __start_storategy(self, storategy: StorategyClient):
        interval_mins = storategy.interval_mins
        if interval_mins > 0:
            interval = interval_mins * 60
            doSleep = True
        else:
            interval = 1
            doSleep = False
            
        if doSleep:
            base_time = datetime.datetime.now()
            target_min = datetime.timedelta(minutes=(interval_mins- base_time.minute % interval_mins))
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
        symbols = storategy.client.symbols
        for symbol in symbols:
            self.results[symbol] = []
            
        while datetime.datetime.now() < self.__end_time and self.done == False:
            start_time = datetime.datetime.now()
            signals = storategy.run(symbols)
            end_time = datetime.datetime.now()
            diff = end_time - start_time
            self.logger.debug(f"took {diff} for caliculate the signal")
            for signal in signals:
                if signal and signal.order_type is not None:
                    if signal.is_close:
                        self.logger.info(f"close signal is raised. {signal}")
                        results = []
                        if signal.is_buy is None:
                            results = storategy.client.close_all_positions(signal.symbol)
                            if results:
                                self.logger.info(f"positions are closed, remaining budget is {storategy.client.market.budget}")
                        elif signal.is_buy == True:
                            results = storategy.client.close_short_positions(signal.symbol)
                            if results:
                                self.logger.info(f"short positions are closed, remaining budget is {storategy.client.market.budget}")
                        elif signal.is_buy == False:
                            results = storategy.client.close_long_positions(signal.symbol)
                            if results:
                                self.logger.info(f"long positions are closed, remaining budget is {storategy.client.market.budget}")
                            
                        if len(results) > 0:
                            for result in results:
                                if result is not None:
                                    if result[1]:
                                        self.logger.info(f"closed result: {result[0]}")
                                        closedCount += 1
                                    else:
                                        self.logger.info(f"pending closed result: {result[0]}")
                                        closedByPendingCount += 1
                                    self.results[symbol].append(result[0][2])
                    else:
                        if signal.is_buy:
                            position = storategy.client.open_trade(signal.is_buy, amount=signal.amount,price=signal.order_price, tp=signal.tp, sl=signal.sl, order_type=signal.order_type, symbol=signal.symbol)
                            self.logger.info(f"long position is opened: {str(position)} based on {signal}, remaining budget is {storategy.client.market.budget}")
                            buySignalCount += 1
                        elif signal.is_buy == False:
                            position = storategy.client.open_trade(is_buy=signal.is_buy, amount=signal.amount, price=signal.order_price, tp=signal.tp, sl=signal.sl, order_type=signal.order_type, symbol=signal.symbol)
                            self.logger.info(f"short position is opened: {str(position)} based on {signal}, remaining budget is {storategy.client.market.budget}")
                            sellSignalCount += 1
            if doSleep:
                base_time = time.time()
                next_time = ((base_time - time.time()) % interval) or interval
                self.logger.debug(f"wait {sleep_time} to run on next frame")
                #time.sleep(next_time)
                if self.event.wait(timeout=next_time):
                    self.logger.info("Close all positions as for ending the storategies.")
                    storategy.client.close_all_positions()
                    break
            if count % 10 == 0:
                self.logger.debug(f"{count+1} times caliculated. {buySignalCount}, {sellSignalCount}, {closedCount}, {closedByPendingCount}")
                print(storategy.client.get_portfolio())
                print(storategy.client.get_budget())
            count+=1
        
        totalSignalCount = len(self.results[symbol])
        if totalSignalCount != 0:
            revenue = sum(self.results[symbol])
            winList = list(filter(lambda x: x >= 0, self.results[symbol]))
            winCount = len(winList)
            winRevenute = sum(winList)
            resultTxt = f"{symbol}, Revenute:{revenue}, signal count: {totalSignalCount}, win Rate: {winCount/totalSignalCount}, plus: {winRevenute}, minus: {revenue - winRevenute}, revenue ratio: {winRevenute/revenue}"
            self.logger.info(resultTxt)
            self.logger.info(f"buy signal raised:{buySignalCount}, sell signal raise:{sellSignalCount}, close signal is handled: {closedCount}, closed by market: {closedByPendingCount}")
            
    def start_storategies(self, wait=True):
        self.__start_time = datetime.datetime.now()
        self.__end_time = self.__start_time + self.__duration
        self.done = False
        
        for storategy in self.storategies:
            if storategy.client.do_render:
                try:
                    self.__start_storategy(storategy)
                except KeyboardInterrupt:
                    self.logger.info("Finish the storategies as KeyboardInterrupt happened")
                    self.event.set()
                    self.done = True
                    exit()
            else:
                t = threading.Thread(target=self.__start_storategy, args=(storategy,), daemon=False)
                t.start()
                self.logger.debug("started storategy")
                if wait:
                    try:
                        ui = input("Please input 'exit' to end the storategies.")
                        if ui.lower() == 'exit':
                            self.event.set()
                            self.done = True
                            if t.is_alive():
                                exit()
                    except KeyboardInterrupt:
                        self.logger.info("Finish the storategies as KeyboardInterrupt happened")
                        self.event.set()
                        self.done = True
                        if t.is_alive():
                            exit()
                
        
    
    def stop_storategies(self):
        self.done = True
    
    def summary(self):
        totalRevenue = 0
        totalWinCount = 0
        totalSignalCount = 0
        totalWinRevenute = 0
        for storategy in self.storategies:
            symbol = storategy.client.symbols[0]
            totalRevenue += sum(self.results[symbol])
            totalSignalCount += len(self.results[symbol])
            winList = list(filter(lambda x: x >= 0, self.results[symbol]))
            totalWinCount += len(winList)
            totalWinRevenute = sum(winList)
        resultTxt = f"Revenute:{totalRevenue}, signal count: {totalSignalCount}, win Rate: {totalWinCount}, plus: {totalWinRevenute}, minus: {totalRevenue - totalWinRevenute}"
        print(resultTxt)