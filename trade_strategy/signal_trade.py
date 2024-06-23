import copy
import datetime
import json
import os
import random

import finance_client as fc
import pandas as pd

from . import strategies

available_modes = ["rating", "random"]


def __close(client: fc.Client, symbol, state):
    symbol = __convert_symbol(symbol)
    position_type = None
    if state == 1:
        position_type = "ask"
    elif state == -1:
        position_type = "bid"
    else:
        print(f"Unkown state: {state} is specified for {symbol}")
    result = client.close_position(symbol=symbol, position_type=position_type)
    price, position_price, price_diff, profit, suc = result
    return suc, (price, position_price, price_diff, profit)


def __order(client: fc.Client, symbol: str, signal: str, state: str):
    symbol = __convert_symbol(symbol)
    if signal == "buy" and state == 0:
        print(f"buy order: {symbol}")
        suc, result = client.open_trade(is_buy=True, amount=1, order_type=0, symbol=symbol)
        return suc, result, 1
    elif signal == "sell" and state == 0:
        print(f"sell order: {symbol}")
        suc, result = client.open_trade(is_buy=False, amount=1, order_type=0, symbol=symbol)
        return suc, result, -1
    elif "close" in signal:
        print(f"close order: {symbol}")
        suc, result = __close(client, symbol, state)
        return suc, result, 0
    elif "base" == signal:
        pass
    else:
        print(f"Unkown signal: {signal} is specified for {symbol} with {state}")
        return False, "unexpected signal", state


def __signal_order(client, signal_df, symbols):
    signal_series = signal_df["signal"]
    state_series = signal_df["state"]
    results = {}
    for symbol in symbols:
        symbol4order = __convert_symbol(symbol)
        signal = None
        try:
            signal = signal_series[symbol]
            state = state_series[symbol]
        except KeyError:
            continue
        if signal is not None:
            suc, result, result_state = __order(client, symbol4order, signal, state)
            if suc:
                results[symbol] = result_state
            else:
                results[symbol] = 0
    return results


def __convert_symbol(symbol: str):
    if ".T" in symbol:
        return symbol.replace(".T", "")
    else:
        return symbol


def __random_order(client, signal_df):
    signals = signal_df["signal"]  # index has symbols, value has buy or sell. order is irrelevant
    symbols = random.sample(list(signals.index), k=len(signals))  # randomize symbols
    return __signal_order(client, signal_df, symbols)


def __add_rating(client, signals, amount_threthold=10, mean_threthold=4):
    if os.path.exists("./symbols_info.json"):
        with open("./symbols_info.json", mode="r") as fp:
            existing_info = json.load(fp)
    else:
        existing_info = {}
    RATING_KEY = "ratings"

    symbol_convertion = {}
    print("determin symbols from signals: ")
    for symbol in signals.index:
        print(symbol)
        # convert Yahoo format for JPN to common format
        new_symbol = __convert_symbol(symbol)
        symbol_convertion[new_symbol] = symbol
    symbols = list(symbol_convertion.keys())
    print(f"add ratings for {symbols}")

    ratings = {}
    if RATING_KEY in existing_info:
        ratings = existing_info[RATING_KEY]

    if hasattr(client, "get_rating"):
        # check if symbol rating is already updated
        new_symbols = []
        existing_rates = {}
        for symbol in symbols:
            if symbol in ratings:
                rate_info = ratings[symbol]
                try:
                    date = rate_info["update_date"]
                    existing_date = datetime.datetime.fromisoformat(date)
                except AttributeError:
                    existing_date = datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%f")
                except Exception:
                    print(f"can't determin update_date of {symbol}")
                    new_symbols.append(symbol)
                    continue
                delta = datetime.datetime.now() - existing_date
                threshold = datetime.timedelta(days=1)
                if delta >= threshold:
                    new_symbols.append(symbol)
                else:
                    existing_rates[symbol] = rate_info
            else:
                new_symbols.append(symbol)
        existing_rates_df = pd.DataFrame()
        if len(existing_rates) > 0:
            existing_rates_df = pd.DataFrame.from_dict(existing_rates, orient="index")
            existing_rates_df = existing_rates_df[["mean", "var", "amount"]]
        new_ratings_df = pd.DataFrame()
        if len(new_symbols) > 0:
            ## assume columns=["mean", "var", "amount"], index=symbols
            print("start adding get_rating with a client for new symbols")
            new_ratings_df = client.get_rating(new_symbols)
        else:
            print("new symbols not found. try to use existing  rating info.")
        rating_df = pd.concat([existing_rates_df, new_ratings_df], axis=0)
        # if provider doesn't provide rating info for some of symbols, it may be not returned.
        if len(rating_df) > 0:
            candidate_df_all = rating_df[rating_df["amount"] > amount_threthold]
            candidate_df = candidate_df_all[candidate_df_all["mean"] > mean_threthold].copy()
            candidate_df.sort_values(by="var", ascending=True, inplace=True)
            org_index = []
            for symbol in candidate_df.index:
                if symbol in symbol_convertion:
                    org_index.append(symbol_convertion[symbol])
                else:
                    print(f"Unexpectedly symbol({symbol}) is not found on symbol_conversion.")
                    org_index.append(symbol)
            candidate_df.index = org_index
            candidate_df = pd.concat([candidate_df, signals.loc[candidate_df.index]], axis=1)

            remaining_df = signals.loc[list(set(signals.index) - set(candidate_df_all.index))]

            try:
                new_ratings = new_ratings_df.to_dict(orient="index")
                update_date = datetime.datetime.now().isoformat()
                for symbol in new_ratings.keys():
                    new_ratings[symbol]["update_date"] = update_date
                ratings.update(new_ratings)
                existing_info[RATING_KEY] = ratings
                with open("./symbols_info.json", mode="w") as fp:
                    json.dump(existing_info, fp)
            except Exception:
                print("failed to save rating info.")
            return True, candidate_df, remaining_df
        else:
            print("failed to get rate. ratings object has no items.")
            return False, None, None
    print("failed to get rate since client has no such feature")
    return False, None, None


def order_by_signals(signals, finance_client: fc.Client, mode="rating"):
    if len(signals) > 0:
        sig_df = pd.DataFrame.from_dict(signals, orient="index")
        sig_sr = sig_df["signal"].dropna()
        sig_df = sig_df.loc[sig_sr.index]
        close_sig_df = sig_df[(sig_df["state"] != 0) & (sig_df["is_close"] == True)]
        # ignore symbols already have
        sig_df = sig_df[(sig_df["state"] == 0) & (sig_df["is_close"] == False)]
        # sig_df = pd.concat([close_sig_df, sig_df], axis=0)
        signals = close_sig_df["signal"]
        states = close_sig_df["state"]
        new_states = {}
        if len(close_sig_df) > 0:
            print(f"start closing positions {list(close_sig_df.index)}")
        for symbol in close_sig_df.index:
            signal = None
            try:
                signal = signals[symbol]
                state = states[symbol]
            except KeyError:
                print(f"key {symbol} not found on signals. continue with next symbol")
                continue
            except Exception:
                print(f"unkown error for {symbol} on order_by_signals. continue with next symbol")
                continue
            suc, result = __close(finance_client, symbol, state)
            new_states[symbol] = 0

        if "state" in sig_df:
            if len(sig_df) > 0:
                if mode == "rating":
                    suc, rating_df, remain_df = __add_rating(finance_client, sig_df)
                    if suc:
                        signals = rating_df["signal"]
                        states = rating_df["state"]
                        print("start ordering based on ratings")
                        for symbol in rating_df.index:
                            signal = None
                            try:
                                signal = signals[symbol]
                                state = states[symbol]
                            except KeyError:
                                continue
                            if signal is not None:
                                suc, result, result_state = __order(finance_client, symbol, signal, state)
                                if suc:
                                    new_states[symbol] = result_state
                        # handle remainings
                        print("start ordering randomly")
                        new_states_rand = __random_order(finance_client, remain_df)
                        new_states.update(new_states_rand)
                    else:
                        print("Failed to get ratings.")
                elif mode == "random":
                    new_states = __random_order(finance_client, sig_df)
                elif mode == "none" or mode is None:
                    pass
                else:
                    raise ValueError(f"Unkown mode {mode} is specified.")
                return new_states
            else:
                print("no signal specified to order.")
        else:
            print("unkown signal format.")
    else:
        print("no signals specified.")


def order_by_signal_file(file_path: str, finance_client: fc.Client, mode="rating"):
    if os.path.exists(file_path):
        with open(file_path) as fp:
            signals = json.load(fp)
        order_by_signals(signals)
    else:
        print("file path doesn't exist")


def __add_state_to_signal(signals, state, symbol):
    """add state to signals file. value of state is handled separately after a client actually open a position"""
    if signals is None:
        return None
    if len(signals) > 1:
        print("signal raised two or more somehow.")
        return None
    elif len(signals) > 0:
        signal = signals[0]
        signal_dict = signal.to_dict()
        signal_dict["state"] = state
        if state == 0:
            print(f"new signal of {symbol}: {signal}")
        elif state == 1 or state == -1:
            if signal_dict["is_close"]:
                print(f"close signal of {symbol}: {signal}")
        return signal_dict
    else:
        return None


def list_signals(
    client: fc.Client, strategy_key: str, data_length=100, candidate_symbols: list = None, idc_processes: list = None, signal_file_path: str = None
):
    strategy = strategies.load_strategy_client(strategy_key, client, idc_processes, {"data_length": data_length})
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
        new_signals = strategy.run(symbol, state)
        signal_dict = __add_state_to_signal(new_signals, state, symbol)
        if signal_dict is not None:
            signals[symbol] = signal_dict
        elif has_history:
            if state == 0:
                signals.pop(symbol)
    with open(signal_file_path, mode="w") as fp:
        json.dump(signals, fp)
    return signals


def system_trade_one_time(
    client: fc.Client, strategy_key: str, data_length=100, candidate_symbols: list = None, idc_processes: list = None, signal_file_path: str = None
):
    list_signals(client, strategy_key, data_length, candidate_symbols, idc_processes, signal_file_path)
    print("start oders")
    order_by_signal_file(signal_file_path, client)


def list_sygnals_with_csv(
    file_paths: list,
    symbols: list,
    strategy_key: str,
    frame: int = 60 * 24,
    data_length: int = 100,
    idc_processes=[],
    ohlc_columns=["Open", "High", "Low", "Close"],
    date_column="Timestamp",
):
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
        client = CSVClient(file, ohlc_columns, date_column=date_column, idc_process=idc_processes, frame=frame, start_index=data_length)
        strategy = strategies.load_strategy_client(strategy_key, client, idc_processes, {"data_length": data_length})

        has_history = False
        symbol = symbols[index]
        if symbol in signals:
            state = int(signals[symbol]["state"])
            has_history = True
        else:
            state = 0
        new_signals = strategy.run(symbol, state)
        signal_dict = __add_state_to_signal(new_signals, state, symbol)
        if signal_dict is not None:
            signals[symbol] = signal_dict
        elif has_history:
            if state == 0:
                print(f"signal of {symbol} is not raise this time. Delete previouse signal {signals[symbol]['signal']}.")
                signals.pop(symbol)
        index += 1
    with open("./signals.json", mode="w") as fp:
        json.dump(signals, fp)
    return signals


def save_signals(signals: dict):
    with open("./signals.json", mode="w") as fp:
        json.dump(signals, fp)


def list_sygnals_with_yahoo(symbols: list, frame, strategy_key: str, data_length: int, idc_processes=[], adjust_close=True, save_signals=True):
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
        try:
            client = YahooClient([symbol], adjust_close=adjust_close, frame=frame, start_index=-1, auto_step_index=False)
        except Exception:
            print(f"failed to get data of {symbol}. continue with next symbol.")
            continue
        strategy = strategies.load_strategy_client(strategy_key, client, _idc_processes, {"data_length": data_length_})

        has_history = False
        if symbol in signals:
            state = int(signals[symbol]["state"])
            has_history = True
        else:
            state = 0
        new_signals = strategy.run(symbol, state)
        signal_dict = __add_state_to_signal(new_signals, state, symbol)
        if signal_dict is not None:
            signals[symbol] = signal_dict
        elif has_history:
            if state == 0:
                print(f"signal of {symbol} is not raise this time. Delete previouse signal {signals[symbol]['signal']}.")
                signals.pop(symbol)
        del client
        del _idc_processes
    if save_signals:
        with open("./signals.json", mode="w") as fp:
            json.dump(signals, fp)
    return signals
