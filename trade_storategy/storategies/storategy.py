import pandas as pd
from trade_storategy.signal import *
            
def macd_cross(position, previouse_trend, data, target_column="Close", signal_column_name="Signal", macd_column_name="MACD"):
    key="macd_cross"
    def __get_macd_trend(data: pd.DataFrame, target_column, signal_column_name, macd_column_name):
        #1:long, -1:short
        if type(data) != type(None) and signal_column_name in data:
                signal = data[signal_column_name].iloc[-1]
                macd = data[macd_column_name].iloc[-1]
                if macd >= signal:
                    return 1, data[target_column].iloc[-1]
                else:
                    return -1, data[target_column].iloc[-1]
        return 0, None
    
    tick_trend, price = __get_macd_trend(data, target_column, signal_column_name, macd_column_name)
    signal = None
    if tick_trend != 0:
        long_short = position
        if previouse_trend == 1 and tick_trend == -1:
            previouse_trend = tick_trend
            if long_short == 1:
                signal = CloseSellSignal(key)
            else:
                signal = SellSignal(key, price=price)
        elif previouse_trend == -1 and tick_trend == 1:
            previouse_trend = tick_trend
            if long_short == -1:
                signal = CloseBuySignal(key, price=price)
            else:
                signal = BuySignal(key, price=price)
        return signal, tick_trend
    return None, 0
        
def macd_renko(position, df:pd.DataFrame, renko_bnum_column, macd_column_column, macd_signal_column, slope_macd_column, slope_signal_column, order_price_column, threshold=2):
    key="macd_renko"
    long_short = position
    signal = None
    if len(df) > 0:
        last_df = df.iloc[-1]
        renko_cons_num = df[renko_bnum_column].iloc[-2:].sum()
        if long_short == 0:
            if renko_cons_num >= threshold and last_df[macd_column_column]>last_df[macd_signal_column] and last_df[slope_macd_column]>last_df[slope_signal_column]:
                signal = BuySignal(std_name=key, price=df[order_price_column].iloc[-1])
            elif renko_cons_num <= -threshold and last_df[macd_column_column]<last_df[macd_signal_column] and last_df[slope_macd_column]<last_df[slope_signal_column]:
                signal = SellSignal(std_name=key, price=df[order_price_column].iloc[-1])
        elif long_short == 1:
            if renko_cons_num <= -threshold/2 and last_df[macd_column_column]<last_df[macd_signal_column] and last_df[slope_macd_column]<last_df[slope_signal_column]:
                signal = CloseSellSignal(std_name=key, price=df[order_price_column].iloc[-1])
            elif last_df[macd_column_column]<last_df[macd_signal_column] and last_df[slope_macd_column]<last_df[slope_signal_column]:
                signal = CloseSignal(std_name=key)
        elif long_short == -1:
            if renko_cons_num >= threshold/2 and last_df[macd_column_column]>last_df[macd_signal_column] and last_df[slope_macd_column]>last_df[slope_signal_column]:
                signal = CloseBuySignal(std_name=key,  price=df[order_price_column].iloc[-1])
            elif last_df[macd_column_column]>last_df[macd_signal_column] and last_df[slope_macd_column]>last_df[slope_signal_column]:
                signal = CloseSignal(std_name=key)
    else:
        print("no data is provided")
    return signal
        
def macd_renko_bb(position, df:pd.DataFrame,
                renko_bnum_column, macd_column_column, macd_signal_column, slope_macd_column, slope_signal_column, order_price_column,
                lower_value_column, mean_value_column, upper_value_column, ask_value, bid_value
                ):
    key = "macd_renko_bb"
    signal = macd_renko(position, df, renko_bnum_column, macd_column_column, macd_signal_column, slope_macd_column, slope_signal_column, order_price_column)
        
    #if signal is raised, check values for stop loss
    if signal is not None:
        #check bolinger band range
        if signal.is_buy is True:
            lower_value = df.iloc[-1][lower_value_column]
            current_rate = ask_value
            mean_value = df.iloc[-1][mean_value_column]
            if current_rate > mean_value:
                print(f"added sl by mean_value: {mean_value}")
                signal.sl = mean_value
            elif current_rate > lower_value:
                print(f"added sl by lower_value: {lower_value}")
                signal.sl = lower_value
            else:
                print("don't add the sl as current value is too low")
                
        elif signal.is_buy is False:#sell case
            print("sell signal is raised. Start adding a sl")
            current_rate = bid_value
            mean_value = df.iloc[-1][mean_value_column]
            upper_value = df.iloc[-1][upper_value_column]
            if current_rate < mean_value:
                print(f"added sl by mean_value: {mean_value}")
                signal.sl = mean_value
            elif current_rate < upper_value:
                print(f"added sl by upper_value: {upper_value}")
                signal.sl = upper_value
            else:
                print("don't add sl as current value is too high")
                
        elif signal.is_close:
            pass
        
        else:            
            print(f"unkown signal type {signal.is_buy}")
            signal = None
            
    return signal
        
def cci_cross(position, df:pd.DataFrame, cci_column_name, order_price_column="Close", boarder=0):
    key = "cci_cross"
    long_short = position
    signal = None
    if len(df) > 0:
        pre_tick = df.iloc[-2]
        last_tick = df.iloc[-1]
        pre_cci = pre_tick[cci_column_name]
        last_cci = last_tick[cci_column_name]
        if long_short == 0:
            if pre_cci > boarder:
                if last_cci < boarder:
                    signal = SellSignal(std_name=key, price=df[order_price_column].iloc[-1])
            else:
                if last_cci > boarder:
                    signal = BuySignal(std_name=key, price=df[order_price_column].iloc[-1])
        elif long_short == 1:
            if last_cci < boarder:
                signal = CloseSellSignal(std_name=key, price=df[order_price_column].iloc[-1])
        elif long_short == -1:
            if last_cci > boarder:
                signal = CloseBuySignal(std_name=key, price=df[order_price_column].iloc[-1])
    return signal
    
def cci_boader(position, df:pd.DataFrame, cci_column_name, order_price_column, upper_boader=100, lower_boader=-100):
    key = "cci_boader"    
    long_short = position
    signal = None
    if len(df) > 0:
        last_df = df.iloc[-1]
        current_cci = last_df[cci_column_name]
        if long_short != 1:
            if current_cci >= upper_boader:
                if current_cci >= upper_boader * 2:
                    print(f"Buy signal is not raised as cci is too high {current_cci}")
                else:
                    print(f"Buy signal is raised as cci over {upper_boader}: {current_cci}")
                    signal = CloseBuySignal(std_name=key, price=df[order_price_column].iloc[-1])
                trend = 1
            elif lower_boader < current_cci:
                trend = 0
                if long_short == -1:
                    signal = CloseSignal(std_name=key, price=df[order_price_column].iloc[-1])
        elif long_short != -1:
            if current_cci <= lower_boader:
                if current_cci <= lower_boader * 2:
                    print(f"Sell signal is not raised as cci is too low {current_cci}")
                else:
                    print(f"Buy signal is raised as cci over -100: {current_cci}")
                    signal = CloseSellSignal(std_name=key, price=df[order_price_column].iloc[-1])
            elif upper_boader > current_cci:
                if long_short == 1:
                    signal = CloseSignal(std_name=key, price=df[order_price_column].iloc[-1])
    return signal
    
def range_experimental(position, df:pd.DataFrame, range_possibility_column, trend_possibility_column, width_column, bb_alpha=2, slope_ratio=0.4, order_price_column="Close"):
    key = "range_ex"
    rp = df[range_possibility_column].iloc[-1]
    tp = df[trend_possibility_column].iloc[-1]
    signal = None
    if rp < 0.6:
        width = df[width_column].iloc[-1]
        std = width/(bb_alpha*2)
        #pending order is not implemented for now...
        if position == 0:
            if tp < - slope_ratio:
                signal = BuySignal(key, df[order_price_column].iloc[-1], tp=df[order_price_column].iloc[-1]+std*4, sl=df[order_price_column].iloc[-1]-std*2)
            elif tp < slope_ratio:#Unbalance
                pass
            else:
                signal = SellSignal(key, df[order_price_column].iloc[-1], sl=df[order_price_column].iloc[-1]+std*2,tp=df[order_price_column].iloc[-1]-std*4)
        elif position == -1:
            if tp < -slope_ratio:
                signal = CloseSignal(key, df[order_price_column].iloc[-1])
            elif tp < slope_ratio:
                signal = CloseSignal(key, df[order_price_column].iloc[-1])
            else:
                #wait as we have long position on long trend
                pass
        else:
            if tp < -slope_ratio:
                #wait as we have short position on short trend
                pass
            elif tp < slope_ratio:
                signal = CloseSignal(key, df[order_price_column].iloc[-1])
            else:
                signal = CloseSignal(key, df[order_price_column].iloc[-1])
    else:
        if position != 0:
            if position == 1 and tp > slope_ratio:
                pass
            elif position == -1 and tp < -slope_ratio:
                pass
            else:
                signal = CloseSignal(key, df[order_price_column].iloc[-1])
                #logger.info("Colose signal as range trend end.")
    return signal
         
def macd_renko_range_ex(position, df:pd.DataFrame, is_in_range,
                        range_possibility_column, renko_bnum_column, macd_column_column, macd_signal_column, slope_macd_column, slope_signal_column,
                        high_column, upper_column, low_column, lower_column, threadh_hold=2,
                        order_price_column="Close"
                        ):
    key="macd_renko_range_ex"
    __is_in_range = is_in_range
    long_short = position
    signal = None
    if len(df) > 0:
        rp = df[range_possibility_column].iloc[-1]
        last_df = df.iloc[-1]
        renko_cont_num = df[renko_bnum_column].iloc[-2:].sum()
        if long_short == 0:
            if renko_cont_num >= threadh_hold and last_df[macd_column_column]>last_df[macd_signal_column] and last_df[slope_macd_column]>last_df[slope_signal_column]:
                if rp <= 0.65:
                    signal = BuySignal(std_name=key, price=df[order_price_column].iloc[-1])
                    trend = 1
                    __is_in_range = False
                else:
                    __is_in_range = True
                    signal = SellSignal(std_name=key, price=df[order_price_column].iloc[-1])
                    trend = -1
            elif renko_cont_num <= -threadh_hold and last_df[macd_column_column]<last_df[macd_signal_column] and last_df[slope_macd_column]<last_df[slope_signal_column]:
                if rp <= 0.65:
                    signal = SellSignal(std_name=key, price=df[order_price_column].iloc[-1])
                    trend = -1
                    __is_in_range = False
                else:
                    signal = BuySignal(std_name=key, price=df[order_price_column].iloc[-1])
                    trend = 1
                    __is_in_range = True
                    
        elif long_short == 1:
            if is_in_range:
                if last_df[high_column] >= last_df[upper_column]:
                        signal = CloseSignal(std_name=key)
            else:
                if renko_cont_num <=-threadh_hold/2 and last_df[macd_column_column]<last_df[macd_signal_column] and last_df[slope_macd_column]<last_df[slope_signal_column]:
                    signal = CloseSellSignal(std_name=key, price=df[order_price_column].iloc[-1])
                    trend = -1
                elif last_df[macd_column_column]<last_df[macd_signal_column] and last_df[slope_macd_column]<last_df[slope_signal_column]:
                    signal = CloseSignal(std_name=key)
                    trend = 0
            if rp <= 0.65:
                __is_in_range = False
                
        elif long_short == -1:
            if is_in_range:
                if last_df[low_column] <= last_df[lower_column]:
                        signal = CloseSignal(std_name=key)
            else:
                if renko_cont_num >=threadh_hold/2 and last_df[macd_column_column]>last_df[macd_signal_column] and last_df[slope_macd_column]>last_df[slope_signal_column]:
                    signal = CloseBuySignal(std_name=key,  price=df[order_price_column].iloc[-1])
                    trend = 1
                elif last_df[macd_column_column]>last_df[macd_signal_column] and last_df[slope_macd_column]>last_df[slope_signal_column]:
                    signal = CloseSignal(std_name=key)
                    trend = 0
            if rp <= 0.65:
                __is_in_range = False
    return signal, __is_in_range
    
def macd_renkorange_bb_ex(position, df:pd.DataFrame, is_in_range,
                        range_possibility_column, renko_bnum_column, macd_column_column, macd_signal_column, slope_macd_column, slope_signal_column,
                        high_column, upper_column, low_column, lower_column, widh_column, b_alpha=2, threshold=2,
                        order_price_column="Close",
                        ):
    key = "bmacd_renkorange_ex"
    signal, __is_in_range = macd_renko_range_ex(position, df, is_in_range, 
                        range_possibility_column, renko_bnum_column, macd_column_column, macd_signal_column, slope_macd_column, slope_signal_column,
                        high_column, upper_column, low_column, lower_column, threshold, order_price_column)
    
    #if signal is raised, check values for stop loss
    if signal is not None:
        #check bolinger band range
        width = df[widh_column].iloc[-1]
        std = width/(b_alpha*2)
        if signal.is_buy is True:
            signal.sl = signal.order_price - std*3
        elif signal.is_buy is False:#sell case
            signal.sl = signal.order_price + std*3
        elif signal.is_close:
            pass
        else:            
            print(f"unkown signal type {signal.is_buy}")
            signal = None
            
    return signal, __is_in_range
