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
                
        while datetime.datetime.now() < self.__end_time and self.done == False:
            start_time = datetime.datetime.now()
            signal = storategy.run()
            end_time = datetime.datetime.now()
            diff = end_time - start_time
            self.logger.debug(f"took {diff} for caliculate the signal")
            if signal and signal.order_type is not None:
                if signal.is_close:
                    results = []
                    if signal.is_buy is None:
                        results = storategy.client.close_all_positions()
                        self.logger.info(f"positions are closed, remaining budget is {storategy.client.market.budget}")
                    elif signal.is_buy == True:
                        results = storategy.client.close_short_positions()
                        self.logger.info(f"short positions are closed, remaining budget is {storategy.client.market.budget}")
                    elif signal.is_buy == False:
                        results = storategy.client.close_long_positions()
                        self.logger.info(f"long positions are closed, remaining budget is {storategy.client.market.budget}")
                        
                    if len(results) > 0:
                        for result in results:
                            if result:
                                self.logger.info(f"closed result: {result}")
                                self.results[storategy.key].append(result[2])
                else:
                    if signal.is_buy:
                        position = storategy.client.open_trade(signal.is_buy, amount=signal.amount,price=signal.order_price, tp=signal.tp, sl=signal.sl, order_type=signal.order_type, symbol="USDJPY")
                        self.logger.info(f"long position is opened: {position} based on {signal}, remaining budget is {storategy.client.market.budget}")
                    elif signal.is_buy == False:
                        position = storategy.client.open_trade(is_buy=signal.is_buy, amount=signal.amount, price=signal.order_price, tp=signal.tp, sl=signal.sl, order_type=signal.order_type, symbol="USDJPY")
                        self.logger.info(f"short position is opened: {position} based on {signal}, remaining budget is {storategy.client.market.budget}")
            if doSleep:
                base_time = time.time()
                next_time = ((base_time - time.time()) % interval) or interval
                self.logger.debug(f"wait {sleep_time} to run on next frame")
                #time.sleep(next_time)
                if self.event.wait(timeout=next_time):
                    self.logger.info("Close all positions as for ending the storategies.")
                    storategy.client.close_all_positions()
                    break
        
        totalSignalCount = len(self.results[storategy.key])
        if totalSignalCount != 0:
            revenue = sum(self.results[storategy.key])
            winList = list(filter(lambda x: x >= 0, self.results[storategy.key]))
            winCount = len(winList)
            winRevenute = sum(winList)
            resultTxt = f"{storategy.key}, Revenute:{revenue}, signal count: {totalSignalCount}, win Rate: {winCount/totalSignalCount}, plus: {winRevenute}, minus: {revenue - winRevenute}, revenue ratio: {winRevenute/revenue}"
            self.logger.info(resultTxt)
            
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
        
class MultiSymbolStorategyManager:
    
    def __init__(self, storategy:StorategyClient, symbols:list, days=0, hours=0, minutes=0,  logger = None) -> None:
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
            storategy.logger = logger
            
        self.results = {}
        self.storategy = storategy
        self.__duration = datetime.timedelta(days=days, hours=hours, minutes=minutes)
        
        if type(symbols) == list and len(symbols) > 0:
            self.symbols = symbols
            for symbol in symbols:
                self.results[symbol] = []
        else:
            raise TypeError("symbols should be valid list.")
        self.done = False
            
    def __start_storategy(self, symbol:str):
        interval_mins = self.storategy.interval_mins
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
        while datetime.datetime.now() < self.__end_time and self.done == False:
            start_time = datetime.datetime.now()
            signal = self.storategy.run(symbols=[symbol])
            end_time = datetime.datetime.now()
            diff = end_time - start_time
            self.logger.debug(f"took {diff} for caliculate the signal")
            if signal and signal.order_type is not None:
                if signal.is_close:
                    results = []
                    if signal.is_buy is None:
                        results = self.storategy.client.close_all_positions()
                        self.logger.info(f"positions are closed, remaining budget is {self.storategy.client.market.budget}")
                    elif signal.is_buy == True:
                        results = self.storategy.client.close_short_positions()
                        self.logger.info(f"short positions are closed, remaining budget is {self.storategy.client.market.budget}")
                    elif signal.is_buy == False:
                        results = self.storategy.client.close_long_positions()
                        self.logger.info(f"long positions are closed, remaining budget is {self.storategy.client.market.budget}")
                        
                    if len(results) > 0:
                        for result in results:
                            if result:
                                self.logger.info(f"closed result: {result}")
                                self.results[self.storategy.key].append(result[2])

                if signal.is_buy:
                    position = self.storategy.client.open_trade(signal.is_buy, amount=signal.amount,price=signal.order_price, tp=signal.tp, sl=signal.sl, order_type=signal.order_type, symbol="USDJPY")
                    self.logger.info(f"long position is opened: {position} based on {signal}, remaining budget is {self.storategy.client.market.budget}")
                elif signal.is_buy == False:
                    position = self.storategy.client.open_trade(is_buy=signal.is_buy, amount=signal.amount, price=signal.order_price, tp=signal.tp, sl=signal.sl, order_type=signal.order_type, symbol="USDJPY")
                    self.logger.info(f"short position is opened: {position} based on {signal}, remaining budget is {self.storategy.client.market.budget}")
            if doSleep:
                base_time = time.time()
                next_time = ((base_time - time.time()) % interval) or interval
                self.logger.debug(f"wait {sleep_time} to run on next frame")
                #time.sleep(next_time)
                if self.event.wait(timeout=next_time):
                    self.logger.info("Close all positions as for ending the storategies.")
                    self.storategy.client.close_all_positions()
                    break
            if count % 10 == 0:
                self.logger.debug(f"{count+1} times caliculated.")
            count+=1
        
        totalSignalCount = len(self.results[self.storategy.key])
        if totalSignalCount != 0:
            revenue = sum(self.results[self.storategy.key])
            winList = list(filter(lambda x: x >= 0, self.results[self.storategy.key]))
            winCount = len(winList)
            winRevenute = sum(winList)
            resultTxt = f"{self.storategy.key}, Revenute:{revenue}, signal count: {totalSignalCount}, win Rate: {winCount/totalSignalCount}, plus: {winRevenute}, minus: {revenue - winRevenute}, revenue ratio: {winRevenute/revenue}"
            self.logger.info(resultTxt)
            
    def start_storategies(self):
        self.__start_time = datetime.datetime.now()
        self.__end_time = self.__start_time + self.__duration
        self.done = False
        
        for symbol in self.symbols:
            if self.storategy.client.do_render:
                try:
                    self.__start_storategy(symbol, )
                except KeyboardInterrupt:
                    self.logger.info("Finish the storategies as KeyboardInterrupt happened")
                    self.event.set()
                    self.done = True
                    exit()
            else:
                t = threading.Thread(target=self.__start_storategy, args=(symbol,), daemon=True)
                t.start()
        
    
    def stop_storategies(self):
        self.done = True