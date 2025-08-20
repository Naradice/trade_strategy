import unittest, os, sys
BASE_PATH = os.path.join(os.path.dirname(__file__), "..")
# for finance_client
module_path = os.path.abspath(f"{BASE_PATH}/../finance_client")
sys.path.append(module_path)
# for trade_strategy
sys.path.append(BASE_PATH)
import trade_strategy as ts
from trade_strategy.signal import BuySignal, SellSignal, CloseBuySignal, CloseSellSignal, CloseSignal, update_signal_with_close

class SignalTest(unittest.TestCase):
    
    def test_update_buysignal_with_close(self):
        buy_signal = BuySignal("unit_test", amount=1, price=1)
        signal = update_signal_with_close(buy_signal)
        self.assertTrue(isinstance(signal, CloseBuySignal))
        self.assertTrue(signal.is_close and signal.is_buy)
    
    def test_update_sellsignal_with_close(self):
        _signal = SellSignal("unit_test", amount=1, price=1)
        signal = update_signal_with_close(_signal)
        self.assertTrue(isinstance(signal, CloseSellSignal))
        self.assertTrue(signal.is_close and signal.is_buy == False)
        
    def test_keep_closesignal_by_update(self):
        _signal = CloseSignal("unit_test")
        signal = update_signal_with_close(_signal)
        self.assertTrue(isinstance(signal, CloseSignal))
        self.assertTrue(signal.is_close and signal.is_buy is None)
    
if __name__ == '__main__':
    unittest.main()