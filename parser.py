import re
from typing import Optional, Dict, Any
from enum import Enum
import logging

class ActionType(Enum):
    BUY = "BUY"
    SELL = "SELL"

def parse_signal(message_text: str) -> Optional[Dict[str, Any]]:
    """
    Parses Turkish trading signals from GOLD BOT PLUS.
    Returns a dictionary with extracted data or None if the message is not a valid entry signal.
    """
    # 1. Ignore "Target Reached" notifications immediately
    if "HEDEFTE" in message_text or "✅" in message_text:
        return None

    # 2. Extract Action Type
    action = None
    upper_text = message_text.upper()
    if "LONG GİR" in upper_text or "BUY" in upper_text:
        action = ActionType.BUY
    elif "SHORT GİR" in upper_text or "SELL" in upper_text:
        action = ActionType.SELL
    
    if not action:
        return None

    # 3. Extract Ticker and Entry Price
    # Matches "OANDA:XAUUSD, price = 3987.930"
    symbol_price_match = re.search(r'OANDA:([A-Z]+)[^p]*price\s*=\s*([0-9.]+)', message_text, re.IGNORECASE)
    
    if not symbol_price_match:
        # Fallback if OANDA format isn't strictly followed, try to extract basic "XAU USD" and price
        return None

    ticker = symbol_price_match.group(1).upper()
    try:
        entry_price = float(symbol_price_match.group(2))
    except ValueError:
        return None

    # 4. Extract Pips Target
    # Matches "HEDEF 100 PİP"
    pip_match = re.search(r'HEDEF\s+(\d+)\s+P[İI]P', upper_text)
    target_pips = int(pip_match.group(1)) if pip_match else 100

    return {
        "ticker": ticker,
        "action": action,
        "entry_price": entry_price,
        "target_pips": target_pips
    }

def calculate_tp_sl(entry_price: float, action: ActionType, target_pips: int, pip_value: float, sl_ratio: float = 1.5) -> tuple[float, float]:
    """
    Calculates Take Profit and Stop Loss absolute prices.
    """
    tp_distance = target_pips * pip_value
    sl_distance = tp_distance * sl_ratio
    
    if action == ActionType.BUY:
        take_profit = entry_price + tp_distance
        stop_loss = entry_price - sl_distance
    else:
        take_profit = entry_price - tp_distance
        stop_loss = entry_price + sl_distance
        
    return round(take_profit, 5), round(stop_loss, 5)

if __name__ == '__main__':
    import unittest

    class TestSignalParser(unittest.TestCase):
        def test_valid_long_signal(self):
            msg = "💵 XAU USD LONG GİR HEDEF 100 PİP ( FİYAT DÜŞERKEN SİNYAL ) OANDA:XAUUSD, price = 3987.930 DateTime = 2023-10-05T12:00:00"
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
            msg = "🚨 XAU USD 100 PİP LONG HEDEFTE ✅"
            self.assertIsNone(parse_signal(msg))
            
        def test_valid_short_signal(self):
            msg = "💵 EUR USD SHORT GİR HEDEF 50 PİP ... OANDA:EURUSD, price = 1.05000"
            res = parse_signal(msg)
            self.assertIsNotNone(res)
            self.assertEqual(res["ticker"], "EURUSD")
            self.assertEqual(res["action"], ActionType.SELL)
            self.assertEqual(res["entry_price"], 1.05000)
            self.assertEqual(res["target_pips"], 50)
            
            tp, sl = calculate_tp_sl(res["entry_price"], res["action"], res["target_pips"], 0.0001, 1.5)
            self.assertEqual(tp, 1.04500)
            self.assertEqual(sl, 1.05750)

    unittest.main()
