import json
from os import path
from time import sleep
from . import storategies
from finance_client.csv.client import CSVClient
from finance_client.yfinance.client import YahooClient
import copy

class SystemTrade:
    
    def __init__(self, clients:list, symbols:list, storategy:storategies.StorategyClient, data_length:int) -> None:
        self.clients = clients
        self.symbols = symbols
        self.st = storategy
        self.data_length = data_length
        
    def list_sygnals(self):
        if path.exists("./signals.json"):
            with open("./signals.json", mode="r") as fp:
                signals = json.load(fp)
        else:
            signals = {}
        index = 0
        for client in self.clients:
            df = client.get_rate_with_indicaters().iloc[-self.data_length:]
            symbol = self.symbols[index]
            if symbol in signals:
                state = int(signals[symbol]["state"])
            else:
                state = 0
            signal = self.st.get_signal(df, state)
            if signal is not None:
                signals[symbol] = {"signal":signal.key, "price":signal.order_price, "state":state}
                print(f"{symbol}: {signal}")
            index += 1
        print("-----------------------------------------")
        print(signals)
        with open("./signals.json", mode="w") as fp:
            json.dump(signals, fp)
        return signals
    
class SystemTradeCSV(SystemTrade):
    
    def __init__(self, file_paths: list, symbols:list, frame:int=60*24, storategy: storategies.StorategyClient = [], data_length: int = 100, idc_processes=[], ohlc_columns=["Open", "High", "Low", "Close"], date_column="Timestamp") -> None:
        
        clients = [CSVClient(file=path, columns=ohlc_columns, date_column=date_column, idc_processes=idc_processes) for path in file_paths]
        super().__init__(clients, symbols, storategy, data_length)
        
    def list_sygnals(self):
        if path.exists("./signals.json"):
            with open("./signals.json", mode="r") as fp:
                signals = json.load(fp)
        else:
            signals = {}
        index = 0
        for client in self.clients:
            ohlc = client.data.iloc[-(self.data_length + 100):]
            df = client.run_processes(ohlc)
            symbol = self.symbols[index]
            if symbol in signals:
                state = int(signals[symbol]["state"])
            else:
                state = 0
            signal = self.st.get_signal(df, state)
            if signal is not None:
                signals[symbol] = {"signal":signal.key, "price":signal.order_price, "state":state}
                print(f"{symbol}: {signal}")
            index += 1
        print("-----------------------------------------")
        print(signals)
        with open("./signals.json", mode="w") as fp:
            json.dump(signals, fp)
        return signals
            
class SystemTradeYahoo():
    
    def __init__(self, symbols: list, frame, storategy: storategies.StorategyClient, data_length: int, idc_processes=[], adjust_close=True) -> None:
        self.symbols = symbols
        self.st = storategy
        self.data_length = data_length
        self.adjust_close = adjust_close
        self.frame = frame
        self.idc_processes = idc_processes
    
    def list_sygnals(self):
        if path.exists("./signals.json"):
            with open("./signals.json", mode="r") as fp:
                signals = json.load(fp)
        else:
            signals = {}
        for symbol in self.symbols:
            idc_processes = copy.copy(self.idc_processes)
            client = YahooClient(symbol, adjust_close=self.adjust_close, frame=self.frame, idc_processes=idc_processes)
            ohlc = client.data.iloc[-(self.data_length+30):]
            ohlc = ohlc.dropna()
            #print("----------------------------------")
            #print(f"caliculation for {symbol}")
            #print(ohlc)
            df = client.run_processes(ohlc)
            #print(df)
            if symbol in signals:
                state = int(signals[symbol]["state"])
            else:
                state = 0
            signal = self.st.get_signal(df, state)
            if signal is not None:
                signals[symbol] = {"signal":signal.key, "price":signal.order_price, "state":state}
                print(f"{symbol}: {signal}")
            del client
            del idc_processes
            del ohlc
            del df
        print("-----------------------------------------")
        print(signals)
        with open("./signals.json", mode="w") as fp:
            json.dump(signals, fp)
        return signals