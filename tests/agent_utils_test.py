import os
import sys
import unittest

import dotenv

BASE_PATH = os.path.join(os.path.dirname(__file__), "..")

# for finance_client
module_path = os.path.abspath(f"{BASE_PATH}/../finance_client")
sys.path.append(module_path)
# for trade_strategy
module_path = os.path.abspath(BASE_PATH)
sys.path.append(module_path)
from trade_strategy.agents.utils import parse_json_string

class TestUtils(unittest.TestCase):
    def test_parse_json_market_trend(self):
        # assume agent responsed with json
        trend_analysis = """
        {
            "trend": "uptrend",
            "strength": "strong",
            "reason": "The 20-period moving average is sloping upward and both highs and lows are rising."
        }
        """
        expected_output = {
            "trend": "uptrend",
            "reason": "The 20-period moving average is sloping upward and both highs and lows are rising.",
            "strength": "strong"
        }
        result = parse_json_string(trend_analysis)
        self.assertEqual(result, expected_output)

    def test_parse_signal_analysis(self):
        signal_analysis = """
        {
            "signal": "Buy",
            "price": 120.15,
            "order_type": "limit",
            "tp": 122.00,
            "sl": 119.00,
            "reason": "The order price is within the recent price range and aligns with market trends."
        }
        """
        expected_output = {
            "signal": "Buy",
            "price": 120.15,
            "order_type": "limit",
            "tp": 122.00,
            "sl": 119.00,
            "reason": "The order price is within the recent price range and aligns with market trends."
        }
        result = parse_json_string(signal_analysis)
        self.assertEqual(result, expected_output)

    def test_parse_text(self):
        text = '```json\n{\n  "signal": "None",\n  "order_type": "limit",\n  "price": 1790.00,\n  "stop_loss": 1680.00,\n  "take_profit": 1850.00,\n  "reason": "Mixed market sentiment and identified risks warrant caution, despite technical indicators suggesting a possible buying opportunity. Therefore, I recommend a \'No Signal\'."\n}\n```'
        result = parse_json_string(text)
        self.assertIsInstance(result, dict)

if __name__ == "__main__":
    unittest.main()