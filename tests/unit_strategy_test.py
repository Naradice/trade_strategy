"""Unit tests for trade_strategy.unit_strategy.

These tests are self-contained: no external data files, no broker connections,
no .env required.  Each test builds a minimal in-memory DataFrame and exercises
the declarative strategy DSL.
"""

import os
import sys
import unittest

import pandas as pd

BASE_PATH = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.abspath(BASE_PATH))

from trade_strategy.unit_strategy import (
    BuyAction,
    BuyLimitAction,
    CloseAction,
    ColumnIndicator,
    ComparisonCondition,
    ConsecutiveCount,
    ConsecutiveCountCondition,
    ConstantIndicator,
    DerivedIndicator,
    LogicalCondition,
    NoAction,
    SellAction,
    StateManager,
    Strategy,
    get_signal,
)
from trade_strategy.signal import BuySignal, CloseSignal, SellSignal


def _make_df(*close_values, extras: dict | None = None) -> pd.DataFrame:
    """Build a minimal OHLC-like DataFrame with a DatetimeIndex."""
    idx = pd.date_range("2024-01-01", periods=len(close_values), freq="1min")
    df = pd.DataFrame({"Close": list(close_values)}, index=idx)
    if extras:
        for col, vals in extras.items():
            df[col] = vals
    return df


# ---------------------------------------------------------------------------
# Indicator
# ---------------------------------------------------------------------------


class TestColumnIndicator(unittest.TestCase):
    def test_returns_last_value(self):
        df = _make_df(1.0, 2.0, 3.0)
        idc = ColumnIndicator("Close")
        self.assertEqual(idc.get_value(df), 3.0)

    def test_cache_same_timestamp(self):
        df = _make_df(1.0, 2.0, 5.0)
        idc = ColumnIndicator("Close")
        val1 = idc.get_value(df)
        # Mutate DataFrame in-place — cache should still return old value
        df["Close"].iloc[-1] = 999.0
        val2 = idc.get_value(df)
        self.assertEqual(val1, val2, "Cache should not recalculate for the same timestamp")

    def test_recalculates_on_new_timestamp(self):
        df1 = _make_df(1.0, 2.0)
        df2 = _make_df(1.0, 2.0, 9.0)
        idc = ColumnIndicator("Close")
        idc.get_value(df1)
        val = idc.get_value(df2)
        self.assertEqual(val, 9.0)


class TestConstantIndicator(unittest.TestCase):
    def test_always_returns_constant(self):
        df = _make_df(42.0)
        idc = ConstantIndicator(10)
        self.assertEqual(idc.get_value(df), 10)


class TestDerivedIndicator(unittest.TestCase):
    def test_subtraction(self):
        df = _make_df(5.0, extras={"Signal": [2.0]})
        macd = ColumnIndicator("Close")
        sig = ColumnIndicator("Signal")
        cross = macd - sig
        self.assertIsInstance(cross, DerivedIndicator)
        self.assertAlmostEqual(cross.get_value(df), 3.0)

    def test_operator_with_constant(self):
        df = _make_df(7.0)
        idc = ColumnIndicator("Close")
        doubled = idc + ConstantIndicator(3)
        self.assertAlmostEqual(doubled.get_value(df), 10.0)


# ---------------------------------------------------------------------------
# Condition
# ---------------------------------------------------------------------------


class TestComparisonCondition(unittest.TestCase):
    def setUp(self):
        self.sm = StateManager()

    def test_gt_true(self):
        df = _make_df(5.0)
        cond = ColumnIndicator("Close") > ConstantIndicator(3.0)
        self.assertIsInstance(cond, ComparisonCondition)
        self.assertTrue(cond.evaluate(df, self.sm))

    def test_gt_false(self):
        df = _make_df(1.0)
        cond = ColumnIndicator("Close") > ConstantIndicator(3.0)
        self.assertFalse(cond.evaluate(df, self.sm))

    def test_lt(self):
        df = _make_df(2.0)
        cond = ColumnIndicator("Close") < ConstantIndicator(3.0)
        self.assertTrue(cond.evaluate(df, self.sm))

    def test_ge_equal(self):
        df = _make_df(3.0)
        cond = ColumnIndicator("Close") >= ConstantIndicator(3.0)
        self.assertTrue(cond.evaluate(df, self.sm))

    def test_le(self):
        df = _make_df(3.0)
        cond = ColumnIndicator("Close") <= ConstantIndicator(3.0)
        self.assertTrue(cond.evaluate(df, self.sm))

    def test_comparison_with_plain_number(self):
        """Operator overload should auto-wrap plain numbers."""
        df = _make_df(5.0)
        cond = ColumnIndicator("Close") > 3
        self.assertTrue(cond.evaluate(df, self.sm))


class TestLogicalCondition(unittest.TestCase):
    def setUp(self):
        self.sm = StateManager()

    def _df(self, close):
        return _make_df(close)

    def test_and_both_true(self):
        df = self._df(5.0)
        cond = (ColumnIndicator("Close") > 3) & (ColumnIndicator("Close") < 10)
        self.assertIsInstance(cond, LogicalCondition)
        self.assertTrue(cond.evaluate(df, self.sm))

    def test_and_one_false(self):
        df = self._df(5.0)
        cond = (ColumnIndicator("Close") > 3) & (ColumnIndicator("Close") > 10)
        self.assertFalse(cond.evaluate(df, self.sm))

    def test_or_one_true(self):
        df = self._df(5.0)
        cond = (ColumnIndicator("Close") > 10) | (ColumnIndicator("Close") > 3)
        self.assertTrue(cond.evaluate(df, self.sm))

    def test_or_both_false(self):
        df = self._df(1.0)
        cond = (ColumnIndicator("Close") > 10) | (ColumnIndicator("Close") > 5)
        self.assertFalse(cond.evaluate(df, self.sm))

    def test_complex_expression(self):
        df = _make_df(5.0, extras={"RSI": [65.0]})
        cond = (ColumnIndicator("Close") > 3) & (ColumnIndicator("RSI") < 70)
        self.assertTrue(cond.evaluate(df, self.sm))


# ---------------------------------------------------------------------------
# StatefulCondition / ConsecutiveCount
# ---------------------------------------------------------------------------


class TestConsecutiveCountCondition(unittest.TestCase):
    def _run_sequence(self, cond_factory, close_values):
        """Evaluate condition once per row; returns list of bool results."""
        sm = StateManager()
        results = []
        for v in close_values:
            df = _make_df(*[v])  # single-row df with the current value
            df.index = pd.date_range("2024-01-01", periods=1, freq="1min") + pd.Timedelta(minutes=len(results))
            cond = cond_factory()
            results.append(cond.evaluate(df, sm))
        return results

    def test_consecutive_count_basic(self):
        sm = StateManager()
        inner = ColumnIndicator("Close") > 0
        cond = ConsecutiveCount(inner) >= 3

        self.assertIsInstance(cond, ConsecutiveCountCondition)

        # Simulate 5 consecutive True evaluations
        for i in range(1, 6):
            df = pd.DataFrame({"Close": [1.0]}, index=pd.date_range("2024-01-01", periods=1, freq="1min") + pd.Timedelta(minutes=i))
            result = cond.evaluate(df, sm)
            if i < 3:
                self.assertFalse(result, f"Should be False at step {i}")
            else:
                self.assertTrue(result, f"Should be True at step {i}")

    def test_count_resets_on_false(self):
        sm = StateManager()
        inner = ColumnIndicator("Close") > 0
        cond = ConsecutiveCount(inner) >= 3

        def _eval(close_val, minute_offset):
            df = pd.DataFrame({"Close": [close_val]}, index=pd.date_range("2024-01-01", periods=1, freq="1min") + pd.Timedelta(minutes=minute_offset))
            return cond.evaluate(df, sm)

        # Two True, then False (resets), then three more True
        _eval(1.0, 1)  # count=1, False
        _eval(1.0, 2)  # count=2, False
        _eval(-1.0, 3)  # reset → count=0, False
        _eval(1.0, 4)  # count=1, False
        _eval(1.0, 5)  # count=2, False
        result = _eval(1.0, 6)  # count=3, True
        self.assertTrue(result)

    def test_consecutive_count_gt(self):
        sm = StateManager()
        inner = ColumnIndicator("Close") > 0
        cond = ConsecutiveCount(inner) > 2  # strictly more than 2

        def _eval(close_val, minute_offset):
            df = pd.DataFrame({"Close": [close_val]}, index=pd.date_range("2024-01-01", periods=1, freq="1min") + pd.Timedelta(minutes=minute_offset))
            return cond.evaluate(df, sm)

        _eval(1.0, 1)  # count=1
        _eval(1.0, 2)  # count=2
        result_at_2 = _eval(1.0, 3)  # count=3, 3>2 → True
        self.assertTrue(result_at_2)


# ---------------------------------------------------------------------------
# StateManager
# ---------------------------------------------------------------------------


class TestStateManager(unittest.TestCase):
    def test_get_default(self):
        sm = StateManager()
        state = sm.get_state("key1", {"count": 0})
        self.assertEqual(state, {"count": 0})

    def test_set_and_get(self):
        sm = StateManager()
        sm.set_state("key1", {"count": 5})
        self.assertEqual(sm.get_state("key1"), {"count": 5})

    def test_reset(self):
        sm = StateManager()
        sm.set_state("key1", {"count": 5})
        sm.reset()
        self.assertIsNone(sm.get_state("key1"))

    def test_default_not_overwritten(self):
        sm = StateManager()
        sm.set_state("key1", {"count": 3})
        state = sm.get_state("key1", {"count": 0})
        self.assertEqual(state["count"], 3, "Existing value should not be replaced by default")


# ---------------------------------------------------------------------------
# Operation
# ---------------------------------------------------------------------------


class TestOperations(unittest.TestCase):
    def setUp(self):
        self.df = _make_df(100.0, extras={"TP": [105.0], "SL": [95.0]})

    def test_no_action(self):
        self.assertIsNone(NoAction().execute(self.df))

    def test_buy_action_market(self):
        signal = BuyAction().execute(self.df)
        self.assertIsInstance(signal, BuySignal)
        self.assertAlmostEqual(signal.order_price, 100.0)

    def test_buy_action_with_tp_sl(self):
        signal = BuyAction(tp_column="TP", sl_column="SL").execute(self.df)
        self.assertIsInstance(signal, BuySignal)
        self.assertAlmostEqual(signal.tp, 105.0)
        self.assertAlmostEqual(signal.sl, 95.0)

    def test_sell_action_market(self):
        signal = SellAction().execute(self.df)
        self.assertIsInstance(signal, SellSignal)
        self.assertAlmostEqual(signal.order_price, 100.0)

    def test_close_action(self):
        signal = CloseAction().execute(self.df)
        self.assertIsInstance(signal, CloseSignal)
        self.assertAlmostEqual(signal.order_price, 100.0)


# ---------------------------------------------------------------------------
# Strategy + get_signal
# ---------------------------------------------------------------------------


class TestStrategy(unittest.TestCase):
    def setUp(self):
        self.sm = StateManager()

    def _df_with_macd(self, macd_val, signal_val, rsi_val, close=100.0, minute_offset: int = 0):
        idx = pd.date_range("2024-01-01", periods=1, freq="1min") + pd.Timedelta(minutes=minute_offset)
        return pd.DataFrame({"Close": [close], "MACD": [macd_val], "Signal": [signal_val], "RSI": [rsi_val]}, index=idx)

    def test_buy_signal_when_condition_true(self):
        macd = ColumnIndicator("MACD")
        sig = ColumnIndicator("Signal")
        rsi = ColumnIndicator("RSI")

        strategy = Strategy(
            condition=(macd - sig > 0) & (rsi < 70),
            true_operation=BuyAction(),
            false_operation=NoAction(),
        )

        df = self._df_with_macd(macd_val=1.0, signal_val=0.5, rsi_val=60.0)
        signal = get_signal(strategy, df, self.sm)
        self.assertIsInstance(signal, BuySignal)

    def test_no_action_when_condition_false(self):
        macd = ColumnIndicator("MACD")
        sig = ColumnIndicator("Signal")
        rsi = ColumnIndicator("RSI")

        strategy = Strategy(
            condition=(macd - sig > 0) & (rsi < 70),
            true_operation=BuyAction(),
            false_operation=NoAction(),
        )

        # RSI is too high
        df = self._df_with_macd(macd_val=1.0, signal_val=0.5, rsi_val=75.0)
        signal = get_signal(strategy, df, self.sm)
        self.assertIsNone(signal)

    def test_nested_strategy(self):
        """Nested Strategy as true_operation of outer Strategy."""
        rsi = ColumnIndicator("RSI")
        macd = ColumnIndicator("MACD")
        sig = ColumnIndicator("Signal")

        inner = Strategy(
            condition=macd - sig > 0,
            true_operation=BuyAction(),
            false_operation=SellAction(),
        )
        outer = Strategy(
            condition=rsi < 70,
            true_operation=inner,
            false_operation=NoAction(),
        )

        # RSI ok, MACD > Signal → Buy  (minute_offset=0)
        df = self._df_with_macd(macd_val=1.0, signal_val=0.5, rsi_val=60.0, minute_offset=0)
        signal = get_signal(outer, df, self.sm)
        self.assertIsInstance(signal, BuySignal)

        # RSI ok, MACD < Signal → Sell  (minute_offset=1 → different timestamp → cache invalidated)
        df2 = self._df_with_macd(macd_val=0.3, signal_val=0.5, rsi_val=60.0, minute_offset=1)
        sm2 = StateManager()
        signal2 = get_signal(outer, df2, sm2)
        self.assertIsInstance(signal2, SellSignal)

        # RSI too high → NoAction  (minute_offset=2)
        df3 = self._df_with_macd(macd_val=1.0, signal_val=0.5, rsi_val=80.0, minute_offset=2)
        sm3 = StateManager()
        signal3 = get_signal(outer, df3, sm3)
        self.assertIsNone(signal3)

    def test_default_false_operation_is_no_action(self):
        """Omitting false_operation defaults to NoAction."""
        strategy = Strategy(
            condition=ColumnIndicator("Close") > 200,
            true_operation=BuyAction(),
        )
        df = _make_df(100.0)
        signal = get_signal(strategy, df, self.sm)
        self.assertIsNone(signal)

    def test_indicator_cache_not_recalculated_in_same_call(self):
        """A shared indicator should calculate() only once per get_signal call."""
        call_count = {"n": 0}
        original_calculate = ColumnIndicator.calculate

        class CountingIndicator(ColumnIndicator):
            def calculate(self, data):
                call_count["n"] += 1
                return super().calculate(data)

        rsi = CountingIndicator("RSI")
        strategy = Strategy(
            condition=(rsi < 70) & (rsi < 80),
            true_operation=BuyAction(),
        )

        df = self._df_with_macd(macd_val=1.0, signal_val=0.5, rsi_val=60.0)
        get_signal(strategy, df, self.sm)
        self.assertEqual(call_count["n"], 1, "calculate() should be called only once due to timestamp caching")


# ---------------------------------------------------------------------------
# Integration: MACD cross strategy
# ---------------------------------------------------------------------------


class TestMACDCrossStrategy(unittest.TestCase):
    """End-to-end test using realistic MACD cross logic."""

    def _build_strategy(self):
        macd = ColumnIndicator("MACD")
        signal_line = ColumnIndicator("macd_Signal")
        rsi = ColumnIndicator("RSI")

        buy_cond = (macd - signal_line > 0) & (rsi < 70)
        sell_cond = (macd - signal_line < 0) & (rsi > 30)

        buy_stg = Strategy(condition=buy_cond, true_operation=BuyAction())
        return Strategy(
            condition=sell_cond,
            true_operation=SellAction(),
            false_operation=buy_stg,
        )

    def _df(self, macd, macd_signal, rsi, close=100.0):
        return pd.DataFrame(
            {"Close": [close], "MACD": [macd], "macd_Signal": [macd_signal], "RSI": [rsi]},
            index=pd.date_range("2024-01-01", periods=1, freq="1min"),
        )

    def test_buy_signal(self):
        strategy = self._build_strategy()
        df = self._df(macd=0.5, macd_signal=0.2, rsi=55)
        signal = get_signal(strategy, df, StateManager())
        self.assertIsInstance(signal, BuySignal)

    def test_sell_signal(self):
        strategy = self._build_strategy()
        df = self._df(macd=-0.2, macd_signal=0.1, rsi=65)
        signal = get_signal(strategy, df, StateManager())
        self.assertIsInstance(signal, SellSignal)

    def test_no_signal_neutral(self):
        strategy = self._build_strategy()
        # MACD > signal_line (not sell) but RSI >= 70 (not buy) → NoAction
        df = self._df(macd=0.5, macd_signal=0.2, rsi=72)
        signal = get_signal(strategy, df, StateManager())
        self.assertIsNone(signal)


if __name__ == "__main__":
    unittest.main()
