from __future__ import annotations

from finance_client.client_base import ClientBase
from finance_client.position import POSITION_SIDE

from ..strategies.strategy_base import StrategyClient
from .state_manager import StateManager
from .strategy import Strategy, get_signal


class UnitStrategyClient(StrategyClient):
    """Adapts the declarative :class:`~.strategy.Strategy` DSL to the imperative
    :class:`~trade_strategy.strategies.strategy_base.StrategyClient` interface so
    that unit-strategy trees can be used directly with
    :class:`~trade_strategy.main.ParallelStrategyManager` and
    :class:`~trade_strategy.main.StrategyRunner`.

    Args:
        finance_client: Any :class:`~finance_client.client_base.ClientBase` instance.
        entry_strategy: Strategy tree evaluated when there is **no** open position.
        exit_long_strategy: Strategy tree evaluated when a **long** position is open.
        exit_short_strategy: Strategy tree evaluated when a **short** position is open.
        exit_strategy: Fallback exit strategy used when the position direction is
            unknown or when direction-specific strategies are not provided.
            When all exit arguments are ``None``, no close signals are generated.
        idc_processes: List of indicator processes to apply to OHLC data.
        interval_mins: Candle interval passed to the base class.
        volume: Trade volume passed through to signals.
        data_length: Number of candles fetched per call.
        trailing_stop: Optional trailing-stop handler.
        logger: Optional logger instance.

    Direction-aware exit example::

        close_long  = Strategy(condition=(cross < 0) | (rsi >= 75), true_operation=CloseAction())
        close_short = Strategy(condition=(cross > 0) | (rsi <= 25), true_operation=CloseAction())

        client_st = UnitStrategyClient(
            finance_client=csv_client,
            entry_strategy=entry,
            exit_long_strategy=close_long,
            exit_short_strategy=close_short,
            idc_processes=[macd_p, rsi_p],
        )

    Shared exit example (direction-agnostic)::

        client_st = UnitStrategyClient(
            finance_client=csv_client,
            entry_strategy=entry,
            exit_strategy=Strategy(condition=(cross < 0) | (cross > 0), true_operation=CloseAction()),
            idc_processes=[macd_p, rsi_p],
        )
    """

    key = "unit_strategy"

    def __init__(
        self,
        finance_client: ClientBase,
        entry_strategy: Strategy,
        exit_long_strategy: Strategy | None = None,
        exit_short_strategy: Strategy | None = None,
        exit_strategy: Strategy | None = None,
        idc_processes: list | None = None,
        interval_mins: int = -1,
        volume: int = 1,
        data_length: int = 100,
        trailing_stop=None,
        logger=None,
    ) -> None:
        super().__init__(
            finance_client=finance_client,
            idc_processes=idc_processes or [],
            interval_mins=interval_mins,
            volume=volume,
            data_length=data_length,
            trailing_stop=trailing_stop,
            logger=logger,
        )
        self._entry_strategy = entry_strategy
        self._exit_long_strategy = exit_long_strategy
        self._exit_short_strategy = exit_short_strategy
        self._exit_strategy = exit_strategy
        self._state_manager = StateManager()

    def get_signal(self, df, position=None, symbol=None):
        """Evaluate entry or exit strategy depending on whether a position is open.

        * **No position** → evaluates *entry_strategy*.
        * **Long position** → evaluates *exit_long_strategy* if set, else *exit_strategy*.
        * **Short position** → evaluates *exit_short_strategy* if set, else *exit_strategy*.

        The same :class:`~.state_manager.StateManager` instance is reused across
        calls so that stateful conditions accumulate correctly over the life of the
        strategy.
        """
        if position is None:
            return get_signal(self._entry_strategy, df, self._state_manager)

        exit_tree = self._resolve_exit(position)
        if exit_tree is not None:
            return get_signal(exit_tree, df, self._state_manager)
        return None

    def _resolve_exit(self, position) -> Strategy | None:
        side = getattr(position, "position_side", None)
        if side == POSITION_SIDE.long and self._exit_long_strategy is not None:
            return self._exit_long_strategy
        if side == POSITION_SIDE.short and self._exit_short_strategy is not None:
            return self._exit_short_strategy
        return self._exit_strategy
