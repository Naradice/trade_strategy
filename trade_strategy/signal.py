from finance_client.position import ORDER_TYPE


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
    def __init__(self, std_name) -> None:
        self.std_name = std_name
        self.key = "base"
        self.trend = Trend()
        self.id = 0
        self.possibility = 0.0
        self.is_buy = None  # just indicate buy or not
        self.order_type = None  # indicate more details of order type not just buy or sell
        self.is_close = False
        self.dev = None
        self.order_price = None
        self.tp = None  # Take Profit price
        self.sl = None  # Stop Loss price
        self.option_info = None
        self.amount = 0
        self.symbol = None

    def __eq__(self, other):
        attr = dir(other)
        # if('id' in attr and 'order_type' in attr):
        if other and dir(self) == dir(other):
            return other.id == self.id
        return False

    def __str__(self) -> str:
        return f"(key={self.key}, symbol={self.symbol}, order_type={self.order_type}, possibility:{self.possibility}, is_close:{self.is_close}, is_buy:{self.is_buy}, order_price:{self.order_price}, tp: {self.tp}, sl:{self.sl}, dev:{self.dev})"

    def to_dict(self, save_option=False) -> dict:
        basic_dict = {
            "id": self.id,
            "symbol": self.symbol,
            "order_type": self.order_type.value,
            "possibility": self.possibility,
            "is_buy": self.is_buy,
            "is_close": self.is_close,
            "dev": self.dev,
            "order_price": self.order_price,
            "tp": self.tp,
            "sl": self.sl,
            "amount": self.amount,
            "symbol": self.symbol,
            "signal": self.key,
        }
        if save_option:
            basic_dict["option"] = self.option_info
        return basic_dict

    @classmethod
    def load_dict(parameters):
        id = parameters["id"]
        amount = parameters["amount"]
        price = parameters["order_price"]
        tp = parameters["tp"]
        sl = parameters["sl"]
        possibility = parameters["possibility"]

        if id == 1:
            return BuySignal("", amount, price, tp, sl)
        elif id == -1:
            return SellSignal("", amount, price, tp, sl)
        elif id == 10:
            return CloseSignal("", price, possibility)
        else:
            print("this id is not supported for now.")


class BuySignal(Signal):
    def __init__(self, std_name, amount=1, price: float = None, tp=None, sl=None, possibility: float = 1.0, symbol=None) -> None:
        super().__init__(std_name)
        self.order_price = price
        self.amount = amount
        self.tp = tp
        self.sl = sl
        self.possibility = possibility
        self.key = "buy"
        self.trend = LongTrend()
        self.id = 1
        self.order_type = ORDER_TYPE.market
        self.is_buy = True
        self.symbol = symbol


class SellSignal(Signal):
    def __init__(self, std_name, amount=1, price: float = None, tp=None, sl=None, possibility: float = 1.0) -> None:
        super().__init__(std_name)
        self.order_price = price
        self.amount = amount
        self.tp = tp
        self.sl = sl
        self.possibility = possibility
        self.key = "sell"
        self.id = -1
        self.trend = ShortTrend()
        self.order_type = ORDER_TYPE.market
        self.is_buy = False


class BuyPendingOrderSignal(Signal):
    def __init__(self, std_name, price: float, amount=1, tp=None, sl=None, possibility: float = 1.0) -> None:
        super().__init__(std_name)
        self.order_price = price
        self.amount = amount
        self.tp = tp
        self.sl = sl
        self.possibility = possibility
        self.key = "buy_pending"
        self.trend = LongTrend()
        self.id = 2
        self.order_type = "Pending"
        self.is_buy = True


class SellPendingOrderSignal(Signal):
    def __init__(self, std_name, price: float, amount=1, tp=None, sl=None, possibility: float = 1.0) -> None:
        super().__init__(std_name)
        self.order_price = price
        self.amount = amount
        self.tp = tp
        self.sl = sl
        self.possibility = possibility
        self.key = "sell_order"
        self.trend = ShortTrend()
        self.id = -2
        self.order_type = "Pending"
        self.is_buy = False


class CloseSignal(Signal):
    "signal to close all position"

    def __init__(self, std_name, price: float = None, possibility: float = 1.0, symbol=None) -> None:
        super().__init__(std_name)

        self.order_price = price
        self.possibility = possibility
        self.symbol = symbol
        self.key = "close"
        self.trend = Trend()
        self.id = 10
        self.order_type = ORDER_TYPE.market
        self.is_buy = None
        self.is_close = True


class CloseBuySignal(Signal):
    "signal to close short position"

    def __init__(self, std_name, amount=1, price: float = None, tp=None, sl=None, possibility: float = 1.0) -> None:
        super().__init__(std_name)
        self.order_price = price
        self.amount = amount
        self.tp = tp
        self.sl = sl
        self.possibility = possibility
        self.key = "close_buy"
        self.id = 11
        self.trend = Trend()
        self.order_type = ORDER_TYPE.market
        self.is_buy = True
        self.is_close = True


class CloseSellSignal(Signal):
    "signal to close short position"

    def __init__(self, std_name, amount=1, price: float = None, tp=None, sl=None, possibility: float = 1.0) -> None:
        super().__init__(std_name)
        self.order_price = price
        self.amount = amount
        self.tp = tp
        self.sl = sl
        self.possibility = possibility
        self.key = "close_sell"
        self.trend = Trend()
        self.id = -11
        self.order_type = ORDER_TYPE.market
        self.is_buy = False
        self.is_close = True


class ValueRangeSignal(Signal):
    def __init__(self, std_name, pricees: list, possibilities: list = None, amount=1) -> None:
        super().__init__(std_name)
        self.order_price = pricees  # [High, Low]
        self.amount = amount
        self.possibility = possibilities
        self.key = ("value_range",)
        self.trend = Trend()
        self.id = 100
        self.order_type = None
        self.is_buy = None


class SignalInfo:
    def __init__(
        self, trend: Trend, is_buy: bool, order_type: str = "Market", amount=1, tp=None, sl=None, price: float = None, possibility: float = 1.0
    ):
        self.trend = trend
        if is_buy:
            if order_type == ORDER_TYPE.market or order_type == "Market" or order_type == ORDER_TYPE.market.value:
                self.signal = BuySignal(amount=amount, tp=tp, sl=sl, possibility=possibility)
            elif order_type == "Pending":
                self.signal = BuyPendingOrderSignal(amount=amount, price=price, tp=tp, sl=sl, possibility=possibility)
        elif is_buy is False:
            if order_type == ORDER_TYPE.market or order_type == "Market" or order_type == ORDER_TYPE.market.value:
                self.signal = SellSignal(amount=amount, tp=tp, sl=sl, possibility=possibility)
            elif order_type == "Pending":
                self.signal = SellPendingOrderSignal(price=price, tp=tp, sl=sl, possibility=possibility)
        elif type(price) == list:
            self.signal = ValueRangeSignal(pricees=price, tp=tp, sl=sl, possibilities=possibility)
        else:
            raise Exception(f"unkown signal info:: is_buy:{is_buy}, price: {price}")


def update_signal_with_close(signal: Signal, continuous_mode: str = None, std_name=None):
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
