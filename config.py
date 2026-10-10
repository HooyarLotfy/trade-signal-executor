import os
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# TELEGRAM CONFIGURATION
# ==========================================
# Get these from https://my.telegram.org
API_ID_RAW = os.getenv("TELEGRAM_API_ID")
API_ID = int(API_ID_RAW) if API_ID_RAW and API_ID_RAW.isdigit() else None
API_HASH = os.getenv("TELEGRAM_API_HASH", None)
SESSION_NAME = os.getenv("TELEGRAM_SESSION_NAME", "trading_bot_session")

# Target channel ID to listen to (e.g. -1001234567890)
TARGET_CHANNEL_ID_RAW = os.getenv("TARGET_CHANNEL_ID")
TARGET_CHANNEL_ID = int(TARGET_CHANNEL_ID_RAW) if TARGET_CHANNEL_ID_RAW and (TARGET_CHANNEL_ID_RAW.isdigit() or TARGET_CHANNEL_ID_RAW.startswith('-')) else None

# ==========================================
# METATRADER 5 CONFIGURATION
# ==========================================
MT5_PATH = os.getenv("MT5_PATH", None)
MT5_LOGIN_RAW = os.getenv("MT5_LOGIN")
MT5_LOGIN = int(MT5_LOGIN_RAW) if MT5_LOGIN_RAW and MT5_LOGIN_RAW.isdigit() else None
MT5_PASSWORD = os.getenv("MT5_PASSWORD", None)
MT5_SERVER = os.getenv("MT5_SERVER", None)

# ==========================================
# TRADING & RISK PARAMETERS
# ==========================================
RISK_PERCENT = float(os.getenv("RISK_PERCENT", "2.0"))
DEFAULT_LOT_SIZE = float(os.getenv("DEFAULT_LOT_SIZE", "0.01"))
AUTO_FIND_SYMBOL = os.getenv("AUTO_FIND_SYMBOL", "True").lower() in ("true", "1", "yes")
SL_RATIO = float(os.getenv("SL_RATIO", "1.5"))
MAX_SLIPPAGE = int(os.getenv("MAX_SLIPPAGE", "10"))

# Suffix or prefix mappings for broker specific symbols
SYMBOL_MAPPING = {
    "XAUUSD": os.getenv("SYMBOL_XAUUSD", "XAUUSD"),
    "GOLD": os.getenv("SYMBOL_GOLD", "XAUUSD"),
    "EURUSD": os.getenv("SYMBOL_EURUSD", "EURUSD"),
    "GBPUSD": os.getenv("SYMBOL_GBPUSD", "GBPUSD"),
}

# Points equivalent to 1 pip per asset class
PIP_VALUES = {
    "XAUUSD": 0.1,
    "EURUSD": 0.0001,
    "GBPUSD": 0.0001,
}
