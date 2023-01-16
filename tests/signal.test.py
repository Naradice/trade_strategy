import unittest, os, json, sys, datetime
module_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(module_path)
import trade_strategy as ts

class SignalTest(unittest.TestCase):
    
    def test_update_buysignal_with_close(self):
        buy_signal = ts.BuySignal("unit_test", amount=1, price=1)
        signal = ts.update_signal_with_close(buy_signal)
        self.assertTrue(isinstance(signal, ts.CloseBuySignal))
        self.assertTrue(signal.is_close and signal.is_buy)
    
    def test_update_sellsignal_with_close(self):
        _signal = ts.SellSignal("unit_test", amount=1, price=1)
        signal = ts.update_signal_with_close(_signal)
        self.assertTrue(isinstance(signal, ts.CloseSellSignal))
        self.assertTrue(signal.is_close and signal.is_buy == False)
        
    def test_keep_closesignal_by_update(self):
        _signal = ts.CloseSignal("unit_test")
        signal = ts.update_signal_with_close(_signal)
        self.assertTrue(isinstance(signal, ts.CloseSignal))
        self.assertTrue(signal.is_close and signal.is_buy is None)
    
if __name__ == '__main__':
    unittest.main()