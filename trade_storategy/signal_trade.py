import copy
import json
import os
import random
import sys

import finance_client as fc
import pandas as pd

from . import storategies

available_modes = ["rating", "random"]

def __close(client:fc.Client, symbol, state):
    position_type = None
    if state == "1":
        position_type = "ask"
    elif state == "-1":
        position_type = "bid"
    else:
        print(f"Unkown state: {state} is specified for {symbol}")
    return client.close_position(symbol=symbol, order_type=position_type)

def __order(client:fc.Client, symbol:str, signal:str, state:str):
    if signal == "buy":
        suc, result =  client.open_trade(is_buy=True, amount=1, order_type="Market", symbol=symbol)
        return suc, result, 1
    elif signal == "sell":
        suc, result = client.open_trade(is_buy=False, amount=1, order_type="Market", symbol=symbol)
        return suc, result, -1
    elif signal == "close":
        suc, result = __close(client, symbol, state)
        return suc, result, 0

def __signal_order(client, signal_df, symbols):
    for symbol in symbols:
        signal = None
        signal_series = signal_df.loc["signal"]
        state_series = signal_df.loc["state"]
        try:
            signal = signal_series[symbol]
            state = state_series[symbol]
        except KeyError:
            continue
        if signal is not None:
            return __order(client, symbol, signal, state)
            
def __random_order(client, signal_df):
    signals = signal_df["signal"]#index has symbols, value has buy or sell. order is irrelevant
    symbols = random.sample(signals.index, k=len(signals))#randomize symbols
    return __signal_order(client, signals, symbols)

def __add_rating(client, signals, amount_threthold=10, mean_threthold=4):
    if hasattr(client, "get_ratings"):
        symbol_convertion = {}
        for symbol in signals.index:
            #convert Yahoo format for JPN to common format
            if ".T" in symbol:
                new_symbol = symbol.replace(".T", "")
                symbol_convertion[new_symbol] = symbol
            else:
                symbol_convertion[symbol] = symbol
        symbols = list(symbol_convertion.values())
        ## assume columns=["mean", "var", "amount"], index=symbols
        ratings = client.get_ratings(symbols)
        # if provider doesn't provide rating info for some of symbols, it may be not returned.
        if len(ratings) > 0:
            candidate_df = ratings[ratings["amount" > amount_threthold]]
            candidate_df = candidate_df[candidate_df["mean" > mean_threthold]]
            candidate_df.sort_values(by="var", ascending=True, inplace=True)
            org_index = []
            for symbol in candidate_df.index:
                if symbol in symbol_convertion:
                    org_index.append(symbol_convertion[symbol])
                else:
                    print(f"Unexpectedly symbol({symbol}) is not found on symbol_conversion.")
                    org_index.append(symbol)
            candidate_df.index = org_index
            
            remaining_df = signals.loc[list(set(signals.index) - set(candidate_df.index))]
            return candidate_df, remaining_df
        else:
            return False, None, None
    return False, None, None

def order_by_signals(signals, finance_client:fc.Client, mode="rating"):
    if len(signals) > 0:
        sig_df = pd.DataFrame.from_dict(signals, orient="index")
        sig_sr = sig_df["signal"].dropna()
        sig_df = sig_df.loc[sig_sr.index]
        if "state" in sig_df:
            if mode == "rating":
                suc, rating_df, remain_df = __add_rating(finance_client, sig_df)
                if suc:
                    signals = rating_df["signal"]
                    for symbol in rating_df.index:
                        signal = None
                        try:
                            signal = signals[symbol]
                        except KeyError:
                            continue
                        if signal is not None:
                            suc, result = __order(finance_client, symbol, signal)
                    ## handle remainings
                    __random_order(finance_client, remain_df)
            elif mode == "random":
                __random_order(finance_client, sig_df)
            else:
                raise ValueError(f"Unkown mode {mode} is specified.")
        else:
            print("unkown signal format.")
    else:
        print("no signals specified.")

def order_by_signal_file(file_path:str, finance_client:fc.Client, mode="rating"):
    if os.path.exists(file_path):
        with open(file_path) as fp:
            signals = json.load(fp)
        order_by_signals(signals)
    else:
        print("file path doesn't exist")
        
def list_signals(client: fc.Client, storategy_key:str, data_length=100, candidate_symbols:list=None, idc_processes:list=None, signal_file_path:str=None):
    storategy = storategies.load_storategy_client(storategy_key, client, idc_processes, {"data_length":data_length})
    if signal_file_path is None:
        signal_file_path = "./signals.json"
    if os.path.exists(signal_file_path):
        with open(signal_file_path, mode="r") as fp:
            signals = json.load(fp)
    else:
        signals = {}
    if candidate_symbols is None:
        candidate_symbols = client.symbols
        
    for symbol in candidate_symbols:
        has_history = False
        if symbol in signals:
            state = int(signals[symbol]["state"])
            has_history = True
        else:
            state = 0
        signal = storategy.run(symbol, state)
        if signal is not None:
            signals[symbol] = signal.to_dict()
        elif has_history:
            if state == 0:
                signals.pop(symbol)
    print("-----------------------------------------")
    print(signals)
    return signals
    
def system_trade_one_time(client: fc.Client, storategy_key:str, data_length=100, candidate_symbols:list=None, idc_processes:list=None, signal_file_path:str=None):
    list_signals(client, storategy_key, data_length, candidate_symbols, idc_processes, signal_file_path)
    print("start oders")
    order_by_signal_file(signal_file_path, client)
    
def list_sygnals_with_csv(file_paths: list, symbols:list, strategy_key:str, frame:int=60*24,
                            data_length: int = 100, idc_processes=[], ohlc_columns=["Open", "High", "Low", "Close"], date_column="Timestamp"):
    from finance_client.csv.client import CSVClient
    if os.path.exists("./signals.json"):
        with open("./signals.json", mode="r") as fp:
            signals = json.load(fp)
    else:
        signals = {}
    index = 0
    for process in idc_processes:
        data_length += process.get_minimum_required_length()
    for file in file_paths:
        client = CSVClient(file, ohlc_columns, date_column=date_column, idc_process=idc_processes, frame=frame)
        storategy = storategies.load_storategy_client(strategy_key, client, idc_processes, {"data_length":data_length})
        
        has_history = False
        symbol = symbols[index]
        if symbol in signals:
            state = int(signals[symbol]["state"])
            has_history = True
        else:
            state = 0
        new_signals = storategy.run(symbol, state)
        if new_signals is not None:
            if len(new_signals) > 1:
                print(f"new_signals raised two or more for a symbol {symbol} somehow.")
            elif len(new_signals) > 0:
                signal = new_signals[0]
                signal_dict = signal.to_dict()
                signal_dict["state"] = state
                signals[symbol] = signal_dict
                print(f"{symbol}: {signal}")
        elif has_history:
            if state == 0:
                print(f"signal of {symbol} is not raise this time. Delete previouse signal {signals[symbol]['signal']}.")
                signals.pop(symbol)
        index += 1
    print("-----------------------------------------")
    print(signals)
    with open("./signals.json", mode="w") as fp:
        json.dump(signals, fp)
    return signals

    
def list_sygnals_with_yahoo(symbols: list, frame, strategy_key:str, data_length: int, idc_processes=[], adjust_close=True):
    from finance_client.yfinance.client import YahooClient
    if os.path.exists("./signals.json"):
        with open("./signals.json", mode="r") as fp:
            signals = json.load(fp)
    else:
        signals = {}
        
    data_length_ = data_length
    for process in idc_processes:
            data_length_ += process.get_minimum_required_length()
    for symbol in symbols:
        
        _idc_processes = copy.copy(idc_processes)
        client = YahooClient([symbol], adjust_close=adjust_close, frame=frame, start_index=-1, auto_step_index=False)
        storategy = storategies.load_storategy_client(strategy_key, client, _idc_processes, {"data_length":data_length_})
        
        has_history = False
        if symbol in signals:
            state = int(signals[symbol]["state"])
            has_history = True
        else:
            state = 0
        new_signals = storategy.run(symbol, state)
        if new_signals is not None:
            if len(new_signals) > 1:
                print(f"new_signals raised two or more for a symbol {symbol} somehow.")
            elif len(new_signals) > 0:
                signal = new_signals[0]
                signal_dict = signal.to_dict()
                signal_dict["state"] = state
                signals[symbol] = signal_dict
                print(f"{symbol}: {signal}")
        elif has_history:
            if state == 0:
                print(f"signal of {symbol} is not raise this time. Delete previouse signal {signals[symbol]['signal']}.")
                signals.pop(symbol)
        del client
        del _idc_processes
    print("-----------------------------------------")
    print(signals)
    with open("./signals.json", mode="w") as fp:
        json.dump(signals, fp)
    return signals