from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


def _wrap(value) -> "Indicator":
    """Wrap a plain numeric value as a ConstantIndicator."""
    if isinstance(value, Indicator):
        return value
    return ConstantIndicator(value)


class Indicator(ABC):
    """Abstract base for market-data indicators.

    Implements lazy evaluation with per-timestamp caching:
    - ``get_value(data)`` checks the latest timestamp in *data*.
    - If the timestamp differs from the cached one, ``calculate(data)`` is called
      and the result is stored.
    - Operator overloads produce :class:`~.condition.ComparisonCondition` objects
      so you can write natural expressions such as ``macd > 0``.
    """

    def __init__(self) -> None:
        self._cache = None
        self._last_timestamp = None

    def get_value(self, data: pd.DataFrame):
        """Return the current indicator value, recalculating only when data is new."""
        timestamp = data.index[-1]
        if self._last_timestamp != timestamp:
            self._cache = self.calculate(data)
            self._last_timestamp = timestamp
        return self._cache

    @abstractmethod
    def calculate(self, data: pd.DataFrame):
        """Compute the indicator value from *data* (called at most once per timestamp)."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Comparison operators → ComparisonCondition (DSL entry points)
    # ------------------------------------------------------------------

    def __gt__(self, other):
        from .condition import ComparisonCondition
        return ComparisonCondition(self, ">", _wrap(other))

    def __lt__(self, other):
        from .condition import ComparisonCondition
        return ComparisonCondition(self, "<", _wrap(other))

    def __ge__(self, other):
        from .condition import ComparisonCondition
        return ComparisonCondition(self, ">=", _wrap(other))

    def __le__(self, other):
        from .condition import ComparisonCondition
        return ComparisonCondition(self, "<=", _wrap(other))

    # ------------------------------------------------------------------
    # Arithmetic operators → DerivedIndicator
    # ------------------------------------------------------------------

    def __sub__(self, other) -> "DerivedIndicator":
        return DerivedIndicator(lambda a, b: a - b, self, _wrap(other))

    def __rsub__(self, other) -> "DerivedIndicator":
        return DerivedIndicator(lambda a, b: a - b, _wrap(other), self)

    def __add__(self, other) -> "DerivedIndicator":
        return DerivedIndicator(lambda a, b: a + b, self, _wrap(other))

    def __radd__(self, other) -> "DerivedIndicator":
        return DerivedIndicator(lambda a, b: a + b, _wrap(other), self)

    def __mul__(self, other) -> "DerivedIndicator":
        return DerivedIndicator(lambda a, b: a * b, self, _wrap(other))

    def __truediv__(self, other) -> "DerivedIndicator":
        return DerivedIndicator(lambda a, b: a / b, self, _wrap(other))


class ConstantIndicator(Indicator):
    """An indicator that always returns a fixed value (used internally for operator overloads)."""

    def __init__(self, value) -> None:
        super().__init__()
        self._value = value

    def calculate(self, data: pd.DataFrame):
        return self._value


class ColumnIndicator(Indicator):
    """Reads the latest value of a named DataFrame column.

    Example::

        macd = ColumnIndicator("MACD")
        signal_line = ColumnIndicator("macd_Signal")
        macd_cross = macd - signal_line   # DerivedIndicator
        condition = macd_cross > 0
    """

    def __init__(self, column: str) -> None:
        super().__init__()
        self.column = column

    def calculate(self, data: pd.DataFrame):
        return data[self.column].iloc[-1]


class DerivedIndicator(Indicator):
    """An indicator computed by applying *func* to the values of one or more other indicators.

    Example::

        cross = DerivedIndicator(lambda a, b: a - b, macd_idc, signal_idc)
    """

    def __init__(self, func, *indicators: Indicator) -> None:
        super().__init__()
        self._func = func
        self._indicators = indicators

    def calculate(self, data: pd.DataFrame):
        values = [ind.get_value(data) for ind in self._indicators]
        return self._func(*values)
