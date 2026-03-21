from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from trade_strategy.signal import BuySignal, SellSignal, CloseSignal, BuyPendingOrderSignal, SellPendingOrderSignal


class Operation(ABC):
    """Terminal action executed after the strategy tree is fully evaluated."""

    @abstractmethod
    def execute(self, data: pd.DataFrame):
        """Return a :class:`~trade_strategy.signal.Signal` or ``None``."""
        raise NotImplementedError


class NoAction(Operation):
    """Do nothing — returns ``None``, meaning no order should be placed."""

    def execute(self, data: pd.DataFrame):
        return None


class BuyAction(Operation):
    """Emit a market buy signal using price (and optionally TP/SL) from named columns.

    Example::

        BuyAction(price_column="Close", sl_column="ATR_SL")
    """

    def __init__(self, price_column: str = "Close", tp_column: str | None = None, sl_column: str | None = None, name: str = "unit_strategy") -> None:
        self._price_column = price_column
        self._tp_column = tp_column
        self._sl_column = sl_column
        self._name = name

    def execute(self, data: pd.DataFrame):
        price = data[self._price_column].iloc[-1]
        tp = data[self._tp_column].iloc[-1] if self._tp_column else None
        sl = data[self._sl_column].iloc[-1] if self._sl_column else None
        return BuySignal(std_name=self._name, price=price, tp=tp, sl=sl)


class SellAction(Operation):
    """Emit a market sell signal.

    Example::

        SellAction(price_column="Close", tp_column="BBAND_lower")
    """

    def __init__(self, price_column: str = "Close", tp_column: str | None = None, sl_column: str | None = None, name: str = "unit_strategy") -> None:
        self._price_column = price_column
        self._tp_column = tp_column
        self._sl_column = sl_column
        self._name = name

    def execute(self, data: pd.DataFrame):
        price = data[self._price_column].iloc[-1]
        tp = data[self._tp_column].iloc[-1] if self._tp_column else None
        sl = data[self._sl_column].iloc[-1] if self._sl_column else None
        return SellSignal(std_name=self._name, price=price, tp=tp, sl=sl)


class BuyLimitAction(Operation):
    """Emit a limit buy (pending) order signal."""

    def __init__(self, price_column: str = "Close", tp_column: str | None = None, sl_column: str | None = None, name: str = "unit_strategy") -> None:
        self._price_column = price_column
        self._tp_column = tp_column
        self._sl_column = sl_column
        self._name = name

    def execute(self, data: pd.DataFrame):
        price = data[self._price_column].iloc[-1]
        tp = data[self._tp_column].iloc[-1] if self._tp_column else None
        sl = data[self._sl_column].iloc[-1] if self._sl_column else None
        return BuyPendingOrderSignal(std_name=self._name, price=price, tp=tp, sl=sl)


class SellLimitAction(Operation):
    """Emit a limit sell (pending) order signal."""

    def __init__(self, price_column: str = "Close", tp_column: str | None = None, sl_column: str | None = None, name: str = "unit_strategy") -> None:
        self._price_column = price_column
        self._tp_column = tp_column
        self._sl_column = sl_column
        self._name = name

    def execute(self, data: pd.DataFrame):
        price = data[self._price_column].iloc[-1]
        tp = data[self._tp_column].iloc[-1] if self._tp_column else None
        sl = data[self._sl_column].iloc[-1] if self._sl_column else None
        return SellPendingOrderSignal(std_name=self._name, price=price, tp=tp, sl=sl)


class CloseAction(Operation):
    """Emit a signal to close the current position at market price."""

    def __init__(self, price_column: str = "Close", name: str = "unit_strategy") -> None:
        self._price_column = price_column
        self._name = name

    def execute(self, data: pd.DataFrame):
        price = data[self._price_column].iloc[-1]
        return CloseSignal(std_name=self._name, price=price)
