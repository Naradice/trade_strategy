from __future__ import annotations

import operator
from abc import ABC, abstractmethod

import pandas as pd

from .state_manager import StateManager

_OPS: dict = {
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
}


class Condition(ABC):
    """Abstract logic gate.  All conditions support ``&`` / ``|`` composition."""

    @abstractmethod
    def evaluate(self, data: pd.DataFrame, state_manager: StateManager) -> bool:
        raise NotImplementedError

    def __and__(self, other: "Condition") -> "LogicalCondition":
        return LogicalCondition(self, "and", other)

    def __or__(self, other: "Condition") -> "LogicalCondition":
        return LogicalCondition(self, "or", other)


class ComparisonCondition(Condition):
    """Evaluates ``indicator <op> threshold``.

    Created automatically when you write expressions such as ``macd_cross > 0``
    (via :meth:`~.indicator.Indicator.__gt__` etc.).

    Both *left* and *right* must be :class:`~.indicator.Indicator` instances
    (plain numbers are auto-wrapped by the operator overloads in
    :class:`~.indicator.Indicator`).
    """

    def __init__(self, left, op: str, right) -> None:
        self.left = left
        self.op = op
        self.right = right

    def evaluate(self, data: pd.DataFrame, state_manager: StateManager) -> bool:
        val = self.left.get_value(data)
        threshold = self.right.get_value(data)
        return _OPS[self.op](val, threshold)


class LogicalCondition(Condition):
    """Combines two conditions with ``and`` / ``or``.

    Created automatically by the ``&`` and ``|`` operators on
    :class:`Condition` subclasses::

        buy_cond = (macd_cross > 0) & (rsi < 80)
    """

    def __init__(self, left: Condition, op: str, right: Condition) -> None:
        self.left = left
        self.op = op  # "and" | "or"
        self.right = right

    def evaluate(self, data: pd.DataFrame, state_manager: StateManager) -> bool:
        left_result = self.left.evaluate(data, state_manager)
        if self.op == "and":
            # Short-circuit: skip right side when left is False
            return left_result and self.right.evaluate(data, state_manager)
        else:
            # Short-circuit: skip right side when left is True
            return left_result or self.right.evaluate(data, state_manager)


class _CountProxy:
    """Intermediate object returned by :func:`ConsecutiveCount` to enable
    comparison syntax::

        ConsecutiveCount(cond) > 3
    """

    def __init__(self, condition: Condition) -> None:
        self._condition = condition

    def __gt__(self, n: int) -> "ConsecutiveCountCondition":
        return ConsecutiveCountCondition(self._condition, n, ">")

    def __ge__(self, n: int) -> "ConsecutiveCountCondition":
        return ConsecutiveCountCondition(self._condition, n, ">=")

    def __lt__(self, n: int) -> "ConsecutiveCountCondition":
        return ConsecutiveCountCondition(self._condition, n, "<")

    def __le__(self, n: int) -> "ConsecutiveCountCondition":
        return ConsecutiveCountCondition(self._condition, n, "<=")

    def __eq__(self, n: int) -> "ConsecutiveCountCondition":  # type: ignore[override]
        return ConsecutiveCountCondition(self._condition, n, "==")


def ConsecutiveCount(condition: Condition) -> _CountProxy:
    """DSL factory — creates a proxy so you can write::

        ConsecutiveCount(macd_cross > 0) >= 3

    This produces a :class:`ConsecutiveCountCondition` that is ``True`` when the
    inner *condition* has been ``True`` for at least 3 consecutive evaluations.
    """
    return _CountProxy(condition)


class ConsecutiveCountCondition(Condition):
    """True when *condition* has been True for N consecutive ``evaluate`` calls.

    State (the running count) is stored in *state_manager* under ``id(self)``,
    so the same inner condition can be reused in multiple wrappers without
    cross-contamination.

    Example::

        three_up_rows = ConsecutiveCount(macd_cross > 0) >= 3
        result = three_up_rows.evaluate(df, state_manager)
    """

    def __init__(self, condition: Condition, count: int, op: str = ">=") -> None:
        self._condition = condition
        self._count = count
        self._op = op

    def evaluate(self, data: pd.DataFrame, state_manager: StateManager) -> bool:
        state = state_manager.get_state(id(self), {"count": 0})
        inner_result = self._condition.evaluate(data, state_manager)
        if inner_result:
            state["count"] += 1
        else:
            state["count"] = 0
        state_manager.set_state(id(self), state)
        return _OPS[self._op](state["count"], self._count)
