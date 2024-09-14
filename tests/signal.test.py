import unittest
import os
import sys

module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(module_path)
import trade_strategy.signal as signal


class SignalTest(unittest.TestCase):
    def test_update_buysignal_with_close(self):
        buy_signal = signal.BuySignal("unit_test", amount=1, price=1)
        s = signal.update_signal_with_close(buy_signal)
        self.assertTrue(isinstance(s, signal.CloseBuySignal))
        self.assertTrue(s.is_close and s.is_buy)

    def test_update_sellsignal_with_close(self):
        _signal = signal.SellSignal("unit_test", amount=1, price=1)
        s = signal.update_signal_with_close(_signal)
        self.assertTrue(isinstance(s, signal.CloseSellSignal))
        self.assertTrue(s.is_close and s.is_buy is False)

    def test_keep_closesignal_by_update(self):
        _signal = signal.CloseSignal("unit_test")
        s = signal.update_signal_with_close(_signal)
        self.assertTrue(isinstance(s, signal.CloseSignal))
        self.assertTrue(s.is_close and s.is_buy is None)


if __name__ == "__main__":
    unittest.main()
