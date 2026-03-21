"""unit_strategy — declarative, composable strategy building blocks.

Quick-start example::

    from trade_strategy.unit_strategy import (
        ColumnIndicator,
        ConsecutiveCount,
        Strategy,
        BuyAction, SellAction, CloseAction, NoAction,
        StateManager,
        get_signal,
    )
    import finance_client.fprocess.fprocess.idcprocess as idcp

    # Indicators (read pre-computed columns from the OHLC DataFrame)
    macd       = ColumnIndicator("MACD")
    macd_sig   = ColumnIndicator("macd_Signal")
    rsi        = ColumnIndicator("RSI")

    # Conditions (lazy — evaluated only when get_signal is called)
    macd_cross_up   = (macd - macd_sig) > 0
    rsi_not_overbought = rsi < 70
    entry_condition = macd_cross_up & rsi_not_overbought

    # Strategy tree
    entry_strategy = Strategy(
        condition=entry_condition,
        true_operation=BuyAction(),
        false_operation=NoAction(),
    )

    # Per-strategy state (create one per live strategy instance)
    sm = StateManager()

    # Each candle
    signal = get_signal(entry_strategy, df, sm)
"""

from .indicator import Indicator, ColumnIndicator, ConstantIndicator, DerivedIndicator
from .condition import (
    Condition,
    ComparisonCondition,
    LogicalCondition,
    ConsecutiveCount,
    ConsecutiveCountCondition,
)
from .state_manager import StateManager
from .operation import Operation, NoAction, BuyAction, SellAction, BuyLimitAction, SellLimitAction, CloseAction
from .strategy import Strategy, get_signal
from .strategy_client import UnitStrategyClient

__all__ = [
    # Indicators
    "Indicator",
    "ColumnIndicator",
    "ConstantIndicator",
    "DerivedIndicator",
    # Conditions
    "Condition",
    "ComparisonCondition",
    "LogicalCondition",
    "ConsecutiveCount",
    "ConsecutiveCountCondition",
    # State
    "StateManager",
    # Operations
    "Operation",
    "NoAction",
    "BuyAction",
    "SellAction",
    "BuyLimitAction",
    "SellLimitAction",
    "CloseAction",
    # Strategy
    "Strategy",
    "get_signal",
    # Bridge to StrategyClient framework
    "UnitStrategyClient",
]
