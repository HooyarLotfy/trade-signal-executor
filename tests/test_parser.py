import unittest
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from parser import parse_signal, calculate_tp_sl, ActionType

class TestSignalParser(unittest.TestCase):
    def test_valid_long_signal(self):
        msg = "XAU USD LONG GİR HEDEF 100 PİP OANDA:XAUUSD, price = 3987.930 DateTime = 2026-10-05T12:00:00"
        res = parse_signal(msg)
        self.assertIsNotNone(res)
        self.assertEqual(res["ticker"], "XAUUSD")
        self.assertEqual(res["action"], ActionType.BUY)
        self.assertEqual(res["entry_price"], 3987.930)
        self.assertEqual(res["target_pips"], 100)
        
        tp, sl = calculate_tp_sl(res["entry_price"], res["action"], res["target_pips"], 0.1, 1.5)
        self.assertEqual(tp, 3997.930)
        self.assertEqual(sl, 3972.930)

    def test_target_reached_ignored(self):
        msg = "XAU USD 100 PİP LONG HEDEFTE"
        self.assertIsNone(parse_signal(msg))
        
    def test_valid_short_signal(self):
        msg = "EUR USD SHORT GİR HEDEF 50 PİP OANDA:EURUSD, price = 1.05000"
        res = parse_signal(msg)
        self.assertIsNotNone(res)
        self.assertEqual(res["ticker"], "EURUSD")
        self.assertEqual(res["action"], ActionType.SELL)
        self.assertEqual(res["entry_price"], 1.05000)
        self.assertEqual(res["target_pips"], 50)
        
        tp, sl = calculate_tp_sl(res["entry_price"], res["action"], res["target_pips"], 0.0001, 1.5)
        self.assertEqual(tp, 1.04500)
        self.assertEqual(sl, 1.05750)

if __name__ == '__main__':
    unittest.main()
