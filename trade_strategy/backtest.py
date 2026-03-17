"""
Synchronous backtest runner for CSVClient-based strategies.

Usage:
    from trade_strategy.backtest import BacktestRunner

    runner = BacktestRunner(strategy, symbols="EURUSD")
    results = runner.run(on_step=lambda n: print(f"Step {n}"))
"""
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
    """

    def __init__(self, strategy: StrategyClient, symbols) -> None:
        self.strategy = strategy
        self.symbols = [symbols] if isinstance(symbols, str) else list(symbols)
        self._runner = StrategyRunner(self.symbols)
        self.step_count = 0

    def run(self, on_step=None) -> dict:
        """
        Execute the strategy against all available data bars.

        Args:
            on_step: optional callable(step_count: int) called after each bar.

        Returns:
            dict mapping symbol -> list[float] of profits for all closed positions.
        """
        self.step_count = 0
        while True:
            try:
                signals = self._runner.get_signals(self.strategy)
                self._runner.handle_signals(self.strategy, signals)
                self.step_count += 1
                if on_step:
                    on_step(self.step_count)
            except StopIteration:
                break
        return self._runner.results
