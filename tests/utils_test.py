import unittest, os, sys
import logging

import dotenv

BASE_PATH = os.path.join(os.path.dirname(__file__), "..")
dotenv.load_dotenv(".env")

# for finance_client
module_path = os.path.abspath(f"{BASE_PATH}/../finance_client")
sys.path.append(module_path)
import finance_client

sys.path.append(BASE_PATH)
from trade_strategy import signal, utils

logger = logging.getLogger("trade_strategy.test")
# enable debug level
logging.basicConfig(level=logging.DEBUG)


class TestUtils(unittest.TestCase):

    def test_trend_to_trend_obj_up(self):
        trend_dict = {
            "trend": "uptrend",
            "reason": "Strong buying pressure",
            "strength": "high"
        }
        trend_obj = utils.trend_to_trend_obj(trend_dict)
        self.assertIsInstance(trend_obj, signal.Trend)
        self.assertEqual(trend_obj.key, signal.TREND_TYPE.up)
        self.assertEqual(trend_obj.reason, "Strong buying pressure")
        self.assertEqual(trend_obj.strength, "high")

    def test_trend_to_trend_obj_down(self):
        trend_dict = {
            "trend": "downtrend",
            "reason": "Strong selling pressure",
            "strength": "high"
        }
        trend_obj = utils.trend_to_trend_obj(trend_dict)
        self.assertIsInstance(trend_obj, signal.Trend)
        self.assertEqual(trend_obj.key, signal.TREND_TYPE.down)
        self.assertEqual(trend_obj.reason, "Strong selling pressure")
        self.assertEqual(trend_obj.strength, "high")

    def test_trend_to_trend_obj_range(self):
        trend_dict = {
            "trend": "ranging",
            "reason": "Price is moving sideways",
            "strength": "medium"
        }
        trend_obj = utils.trend_to_trend_obj(trend_dict)
        self.assertIsInstance(trend_obj, signal.Trend)
        self.assertEqual(trend_obj.key, signal.TREND_TYPE.range)
        self.assertEqual(trend_obj.reason, "Price is moving sideways")
        self.assertEqual(trend_obj.strength, "medium")

    def test_trend_to_trend_obj_sideways(self):
        trend_dict = {
            "trend": "sideways",
            "reason": "Price is moving sideways",
            "strength": "low"
        }
        trend_obj = utils.trend_to_trend_obj(trend_dict)
        self.assertIsInstance(trend_obj, signal.Trend)
        self.assertEqual(trend_obj.key, signal.TREND_TYPE.sideways)
        self.assertEqual(trend_obj.reason, "Price is moving sideways")
        self.assertEqual(trend_obj.strength, "low")

    def test_refine_signal_buy_to_buy(self):
        signal_item = signal.BuySignal("test_strategy", symbol="1333.T")
        signal_dict = {
            "signal": "Buy",
            "order_type": "market",
            "price": 120.15,
            "confidence": 0.8,
            "stop_loss": 119.00,
            "take_profit": 122.00,
            "reason": "The order price is within the recent price range and aligns with market trends."
        }
        refined_signal = utils.refine_signal(signal_item, signal_dict)
        self.assertIsInstance(refined_signal, signal.BuySignal)
        self.assertEqual(refined_signal.confidence, 0.8)
        self.assertEqual(refined_signal.order_price, 120.15)

    def test_refine_signal_sell_to_sell(self):
        signal_item = signal.SellSignal("test_strategy", symbol="1333.T")
        signal_dict = {
            "signal": "Sell",
            "order_type": "market",
            "price": 120.15,
            "confidence": 0.8,
            "stop_loss": 119.00,
            "take_profit": 122.00,
            "reason": "The order price is within the recent price range and aligns with market trends."
        }
        refined_signal = utils.refine_signal(signal_item, signal_dict)
        self.assertIsInstance(refined_signal, signal.SellSignal)
        self.assertEqual(refined_signal.confidence, 0.8)
        self.assertEqual(refined_signal.order_price, 120.15)
    
    def test_refine_signal_close_to_close(self):
        signal_item = signal.CloseSignal("test_strategy", symbol="1333.T")
        signal_dict = {
            "signal": "Buy",
            "order_type": "market",
            "price": 120.15,
            "confidence": 0.8,
            "stop_loss": 119.00,
            "take_profit": 122.00,
            "reason": "The order price is within the recent price range and aligns with market trends."
        }
        refined_signal = utils.refine_signal(signal_item, signal_dict)
        self.assertIsInstance(refined_signal, signal.CloseSignal)
        self.assertEqual(refined_signal.confidence, 0.8)
        self.assertEqual(refined_signal.order_price, 120.15)
    
    def test_refine_signal_buy_to_sell(self):
        signal_item = signal.BuySignal("test_strategy", symbol="1333.T")
        signal_dict = {
            "signal": "Sell",
            "order_type": "market",
            "price": 120.15,
            "confidence": 0.8,
            "stop_loss": 119.00,
            "take_profit": 122.00,
            "reason": "The order price is within the recent price range and aligns with market trends."
        }
        refined_signal = utils.refine_signal(signal_item, signal_dict)
        self.assertIsInstance(refined_signal, signal.SellSignal)
        self.assertEqual(refined_signal.confidence, 0.8)
        self.assertEqual(refined_signal.order_price, 120.15)

    def test_refine_signal_sell_to_buy(self):
        signal_item = signal.SellSignal("test_strategy", symbol="1333.T")
        signal_dict = {
            "signal": "Buy",
            "order_type": "market",
            "price": 120.15,
            "confidence": 0.8,
            "stop_loss": 119.00,
            "take_profit": 122.00,
            "reason": "The order price is within the recent price range and aligns with market trends."
        }
        refined_signal = utils.refine_signal(signal_item, signal_dict)
        self.assertIsInstance(refined_signal, signal.BuySignal)
        self.assertEqual(refined_signal.confidence, 0.8)
        self.assertEqual(refined_signal.order_price, 120.15)

    def test_refine_signal_buy_to_pending_buy(self):
        signal_item = signal.BuySignal("test_strategy", symbol="1333.T")
        signal_dict = {
            "signal": "Buy",
            "order_type": "limit",
            "price": 120.15,
            "confidence": 0.8,
            "stop_loss": 119.00,
            "take_profit": 122.00,
            "reason": "The order price is within the recent price range and aligns with market trends."
        }
        refined_signal = utils.refine_signal(signal_item, signal_dict)
        self.assertIsInstance(refined_signal, signal.BuyPendingOrderSignal)
        self.assertEqual(refined_signal.confidence, 0.8)
        self.assertEqual(refined_signal.order_price, 120.15)

    def test_refine_signal_buy_to_pending_sell(self):
        signal_item = signal.BuySignal("test_strategy", symbol="1333.T")
        signal_dict = {
            "signal": "Sell",
            "order_type": "limit",
            "price": 120.15,
            "confidence": 0.8,
            "stop_loss": 119.00,
            "take_profit": 122.00,
            "reason": "The order price is within the recent price range and aligns with market trends."
        }
        refined_signal = utils.refine_signal(signal_item, signal_dict)
        self.assertIsInstance(refined_signal, signal.SellPendingOrderSignal)
        self.assertEqual(refined_signal.confidence, 0.8)
        self.assertEqual(refined_signal.order_price, 120.15)

    def test_refine_signal_sell_to_pending_buy(self):
        signal_item = signal.SellSignal("test_strategy", symbol="1333.T")
        signal_dict = {
            "signal": "Buy",
            "order_type": "limit",
            "price": 120.15,
            "confidence": 0.8,
            "stop_loss": 119.00,
            "take_profit": 122.00,
            "reason": "The order price is within the recent price range and aligns with market trends."
        }
        refined_signal = utils.refine_signal(signal_item, signal_dict)
        self.assertIsInstance(refined_signal, signal.BuyPendingOrderSignal)
        self.assertEqual(refined_signal.confidence, 0.8)
        self.assertEqual(refined_signal.order_price, 120.15)

    def test_refine_signal_sell_to_pending_sell(self):
        signal_item = signal.SellSignal("test_strategy", symbol="1333.T")
        signal_dict = {
            "signal": "Sell",
            "order_type": "limit",
            "price": 120.15,
            "confidence": 0.8,
            "stop_loss": 119.00,
            "take_profit": 122.00,
            "reason": "The order price is within the recent price range and aligns with market trends."
        }
        refined_signal = utils.refine_signal(signal_item, signal_dict)
        self.assertIsInstance(refined_signal, signal.SellPendingOrderSignal)
        self.assertEqual(refined_signal.confidence, 0.8)
        self.assertEqual(refined_signal.order_price, 120.15)


if __name__ == "__main__":
    unittest.main()