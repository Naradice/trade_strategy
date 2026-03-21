from __future__ import annotations

import pandas as pd

from .condition import Condition
from .operation import Operation, NoAction
from .state_manager import StateManager


class Strategy:
    """A declarative decision node in a composite strategy tree.

    Attributes:
        condition: A :class:`~.condition.Condition` evaluated against market data.
        true_operation: Executed (or recursed into) when *condition* is ``True``.
        false_operation: Executed (or recursed into) when *condition* is ``False``.
            Defaults to :class:`~.operation.NoAction` (returns ``None``).

    Example::

        from trade_strategy.unit_strategy import (
            ColumnIndicator, Strategy, BuyAction, SellAction, NoAction, StateManager
        )

        macd = ColumnIndicator("MACD")
        signal_line = ColumnIndicator("macd_Signal")
        rsi = ColumnIndicator("RSI")

        entry = Strategy(
            condition=(macd - signal_line > 0) & (rsi < 70),
            true_operation=BuyAction(),
            false_operation=NoAction(),
        )

        sm = StateManager()
        signal = get_signal(entry, df, sm)
    """

    def __init__(self, condition: Condition, true_operation: Operation | "Strategy", false_operation: Operation | "Strategy" | None = None) -> None:
        self.condition = condition
        self.true_operation = true_operation
        self.false_operation = false_operation if false_operation is not None else NoAction()


def get_signal(strategy: Strategy, data: pd.DataFrame, state_manager: StateManager):
    """Recursively evaluate *strategy* and return a :class:`~trade_strategy.signal.Signal` or ``None``.

    Execution flow:

    1. Evaluate ``strategy.condition`` against *data*.
    2. Select the appropriate branch (``true_operation`` or ``false_operation``).
    3. If the branch is another :class:`Strategy`, recurse (step 1).
    4. If the branch is a terminal :class:`~.operation.Operation`, call
       ``execute(data)`` and return the result.

    Args:
        strategy: Root node of the strategy tree.
        data: OHLC DataFrame (with indicator columns pre-applied).
        state_manager: Shared state store passed through the entire evaluation.

    Returns:
        A :class:`~trade_strategy.signal.Signal` instance, or ``None`` if no
        action should be taken.
    """
    result = strategy.condition.evaluate(data, state_manager)
    branch = strategy.true_operation if result else strategy.false_operation
    if isinstance(branch, Strategy):
        return get_signal(branch, data, state_manager)
    return branch.execute(data)
