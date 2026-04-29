"""
Synchronous backtest runner for CSVClient-based strategies.

Usage:
    from trade_strategy.backtest import BacktestRunner

    runner = BacktestRunner(strategy, symbols="EURUSD")
    results = runner.run(on_step=lambda n: print(f"Step {n}"))
"""
import pandas as pd
from finance_client.position import ORDER_TYPE
from trade_strategy.main import StrategyRunner
from trade_strategy.strategies import StrategyClient


class BacktestRunner:
    """
    Steps through all available data bars in a CSVClient (auto_step_index=True)
    and executes strategy signals on each bar until StopIteration.

    Unlike ParallelStrategyManager, this runner is:
    - Synchronous (no threading)
    - Stops cleanly when data is exhausted (StopIteration)
    - Suitable for programmatic/server-side backtest execution

    Signals generated at the close of bar N are executed at the open of bar N+1,
    reflecting realistic market entry rather than the lookahead-biased close price.
    If no next bar exists (end of data), the signal is discarded rather than filled
    at an unreachable close price.
    """

    def __init__(self, strategy: StrategyClient, symbols) -> None:
        self.strategy = strategy
        self.symbols = [symbols] if isinstance(symbols, str) else list(symbols)
        self._runner = StrategyRunner(self.symbols)
        self.step_count = 0

    def _next_open_prices(self) -> dict:
        """Return the open price of the next (not-yet-processed) candle per symbol.

        After get_ohlc() increments _step_index, data.iloc[_step_index - 1] is the
        candle not yet returned — i.e., the next bar. Returns {} at end of data.
        """
        client = self.strategy.client
        if not (hasattr(client, "_step_index") and hasattr(client, "data")):
            return {}
        idx = client._step_index - 1
        if idx >= len(client.data):
            return {}
        ohlc = client.get_ohlc_columns()
        open_col = ohlc.get("Open", "Open") if isinstance(ohlc, dict) else "Open"
        row = client.data.iloc[idx]
        if isinstance(client.data.columns, pd.MultiIndex):
            result = {}
            for sym in self.symbols:
                for key in [(sym, open_col), (open_col, sym)]:
                    if key in client.data.columns:
                        result[sym] = row[key]
                        break
            return result
        price = row.get(open_col)
        if price is None:
            return {}
        return {sym: price for sym in self.symbols}

    def _apply_next_open(self, signals: list, next_opens: dict) -> None:
        """Override order_price with the next bar's open for market entry signals."""
        for signal in signals:
            if signal and signal.order_type == ORDER_TYPE.market and signal.id != 10:
                price = next_opens.get(signal.symbol)
                if price is not None:
                    signal.order_price = price

    def run(self, on_step=None) -> dict:
        """
        Execute the strategy against all available data bars.

        Signals from bar N are buffered and executed at bar N+1's open price.
        This prevents lookahead bias from using the bar-N close as the fill price.

        Args:
            on_step: optional callable(step_count: int) called after each bar.

        Returns:
            dict mapping symbol -> list[float] of profits for all closed positions.
        """
        self.step_count = 0
        pending_signals = []
        while True:
            try:
                # Execute signals from the previous bar at the current bar's open.
                if pending_signals:
                    self._runner.handle_signals(self.strategy, pending_signals)
                    pending_signals = []

                signals = self._runner.get_signals(self.strategy)

                # After get_ohlc() increments _step_index, data.iloc[_step_index - 1]
                # is the next bar. Override market entry prices with that open.
                next_opens = self._next_open_prices()
                if next_opens:
                    self._apply_next_open(signals, next_opens)
                    pending_signals = signals
                # If next_opens is empty (end of data), signals are discarded:
                # there is no next bar at which they could realistically be filled.

                self.step_count += 1
                if on_step:
                    on_step(self.step_count)
            except StopIteration:
                break
        return self._runner.results
