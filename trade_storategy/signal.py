PendingOrderKey = "Pending"
MarketOrderKey = "Market"

class Trend:
    key = "base"
    id = 0
    
    def __eq__(self, other):
        return other.id == self.id
    
    def __str__(self) -> str:
        return str(id)
    
class LongTrend(Trend):
    key = "long"
    id = 1
    
class ShortTrend(Trend):
    key = "short"
    id = -1
    
class Signal:
    key = "base"
    trend = Trend()
    id = 0
    possibility = 0.0
    order_type = None
    is_buy = None
    is_close = False
    dev = None
    order_price = None
    tp = None#Take Profit price
    sl = None#Stop Loss price
    option_info = None
    order_price = None
    amount = 0
    symbol = None
    
    def __init__(self, std_name) -> None:
        self.std_name = std_name
    
    def __eq__(self, other):
        attr = dir(other)
        #if('id' in attr and 'order_type' in attr):
        if(other and dir(self) == dir(other)):
            return other.id == self.id
        return False
    
    def __str__(self) -> str:
        return f"(key={self.key}, symbol={self.symbol}, order_type={self.order_type}, possibility:{self.possibility}, is_close:{self.is_close}, is_buy:{self.is_buy}, order_price:{self.order_price}, tp: {self.tp}, sl:{self.sl}, dev:{self.dev})"
    
class BuySignal(Signal):
    key = "buy"
    trend = LongTrend()
    id = 1
    order_type = MarketOrderKey
    is_buy = True
    
    def __init__(self, std_name, amount=1, price:float=None, tp=None, sl=None, possibility:float=1.0) -> None:
        super().__init__(std_name)
        self.order_price = price
        self.amount = amount
        self.tp = tp
        self.sl = sl
        self.possibility = possibility
    
class SellSignal(Signal):
    key = "sell"
    id = -1
    trend = ShortTrend()
    order_type = MarketOrderKey
    is_buy = False
    
    def __init__(self, std_name, amount=1, price:float=None, tp=None, sl=None, possibility:float=1.0) -> None:
        super().__init__(std_name)
        self.order_price = price
        self.amount = amount
        self.tp = tp
        self.sl = sl
        self.possibility = possibility
        
class BuyPendingOrderSignal(Signal):
    key = "buy_pending",
    trend = LongTrend()
    id = 2
    order_type = PendingOrderKey
    is_buy = True
    
    def __init__(self, std_name, price:float, amount=1, tp=None, sl=None,  possibility:float=1.0) -> None:
        super().__init__(std_name)
        self.order_price = price
        self.amount = amount
        self.tp = tp
        self.sl = sl
        self.possibility = possibility

class SellPendingOrderSignal(Signal):
    key = "sell_order",
    trend = ShortTrend()
    id = -2
    order_type = PendingOrderKey
    is_buy = False
    
    def __init__(self, std_name,price:float, amount=1, tp=None, sl=None, possibility:float=1.0) -> None:
        super().__init__(std_name)
        self.order_price = price
        self.amount = amount
        self.tp = tp
        self.sl = sl
        self.possibility = possibility
        
class CloseSignal(Signal):
    "signal to close all position"
    key = "close"
    trend = Trend()
    id = 10
    order_type = MarketOrderKey
    is_buy = None
    is_close = True
    
    def __init__(self, std_name, price:float=None, possibility:float=1.0) -> None:
        super().__init__(std_name)
        self.order_price = price
        self.possibility = possibility

class CloseBuySignal(Signal):
    "signal to close short position"
    key = "close_buy"
    trend = Trend()
    id = 11
    order_type = MarketOrderKey
    is_buy = True
    is_close = True
    
    def __init__(self, std_name, amount=1, price:float=None, tp=None, sl=None, possibility:float=1.0) -> None:
        super().__init__(std_name)
        self.order_price = price
        self.amount = amount
        self.tp = tp
        self.sl = sl
        self.possibility = possibility
        
class CloseSellSignal(Signal):
    "signal to close short position"
    key = "close_sell"
    trend = Trend()
    id = -11
    order_type = MarketOrderKey
    is_buy = False
    is_close = True
    
    def __init__(self, std_name, amount=1, price:float=None, tp=None, sl=None, possibility:float=1.0) -> None:
        super().__init__(std_name)
        self.order_price = price
        self.amount = amount
        self.tp = tp
        self.sl = sl
        self.possibility = possibility

class ValueRangeSignal(Signal):
    key = "value_range",
    trend = Trend()
    id = 100
    order_type = None
    is_buy = None
    
    def __init__(self, std_name, pricees:list, possibilities:list=None, amount=1) -> None:
        super().__init__(std_name)
        self.order_price = pricees#[High, Low]
        self.amount = amount
        self.possibility = possibilities    
    
class SignalInfo:
    
    def __init__(self, trend:Trend, is_buy:bool, order_type: str="Market", amount=1, tp=None, sl=None, price:float=None, possibility:float=1.0):
        self.trend = trend
        if is_buy:
            if order_type == MarketOrderKey:
                self.signal = BuySignal(amount=amount, tp=tp, sl=sl, possibility=possibility)
            elif order_type == PendingOrderKey:
                self.signal = BuyPendingOrderSignal(amount=amount, price=price, tp=tp, sl=sl, possibility=possibility)
        elif is_buy == False:
            if order_type == MarketOrderKey:
                self.signal = SellSignal(amount=amount, tp=tp, sl=sl, possibility=possibility)
            elif order_type == PendingOrderKey:
                self.signal = SellPendingOrderSignal(price=price, tp=tp, sl=sl, possibility=possibility)
        elif type(price) == list:
                self.signal = ValueRangeSignal(pricees=price, tp=tp, sl=sl,  possibilities=possibility)
        else:
            raise Exception(f"unkown signal info:: is_buy:{is_buy}, price: {price}")
        
def update_signal_with_close(signal:Signal, continuous_mode:str = None, std_name = None):
    if std_name is None and signal is not None:
        std_name = signal.std_name
    
    if isinstance(signal, BuySignal):
        return CloseBuySignal(std_name, amount=signal.amount, price=signal.order_price, tp=signal.tp, sl=signal.sl, possibility=signal.possibility)
    elif isinstance(signal, SellSignal):
        return CloseSellSignal(std_name, amount=signal.amount, price=signal.order_price, tp=signal.tp, sl=signal.sl, possibility=signal.possibility)
    elif signal is None:
        if continuous_mode is None:
            return CloseSignal(std_name=std_name)
        elif continuous_mode == "long" or continuous_mode == "ask":
            return CloseBuySignal(std_name=std_name)
        elif continuous_mode == "short" or continuous_mode == "bid":
            return CloseSellSignal(std_name=std_name)
    else:
        if signal.is_close is not None and signal.is_close == False:
            # need to implement pending case
            raise Exception(f"{signal} can't be updated with close.")
        return signal