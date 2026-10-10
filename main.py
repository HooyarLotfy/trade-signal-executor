import asyncio
import logging
import sqlite3
from logging.handlers import RotatingFileHandler
from telethon import TelegramClient, events

# Graceful MT5 import for dev environments without MT5 installed
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    logging.warning("MetaTrader5 module not installed. Mocking execution for testing.")

import config
from parser import parse_signal, calculate_tp_sl, ActionType

# ==========================================
# LOGGING SETUP
# ==========================================
logger = logging.getLogger("TradingBot")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler("trading_bot.log", maxBytes=5*1024*1024, backupCount=2)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.addHandler(logging.StreamHandler())

# ==========================================
# DATABASE SETUP (State Management)
# ==========================================
def init_db():
    conn = sqlite3.connect("bot_state.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS processed_messages (
            message_id INTEGER PRIMARY KEY,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    return conn

def is_message_processed(conn, message_id: int) -> bool:
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM processed_messages WHERE message_id = ?', (message_id,))
    return cursor.fetchone() is not None

def mark_message_processed(conn, message_id: int):
    cursor = conn.cursor()
    cursor.execute('INSERT INTO processed_messages (message_id) VALUES (?)', (message_id,))
    conn.commit()

# ==========================================
# MT5 EXECUTION ENGINE
# ==========================================
def resolve_symbol(raw_symbol: str) -> str:
    """Finds the correct symbol on the broker even if it has a suffix (e.g. XAUUSD.pro)"""
    if not MT5_AVAILABLE:
        return raw_symbol
        
    symbols = mt5.symbols_get()
    if not symbols:
        return config.SYMBOL_MAPPING.get(raw_symbol, raw_symbol)
        
    for s in symbols:
        if s.name == raw_symbol or s.name.startswith(raw_symbol):
            return s.name
            
    return config.SYMBOL_MAPPING.get(raw_symbol, raw_symbol)

def calculate_lot_size(symbol: str, sl_price: float, entry_price: float) -> float:
    """Calculates lot size based on Risk % of Account Balance."""
    if not MT5_AVAILABLE:
        return config.DEFAULT_LOT_SIZE
        
    account = mt5.account_info()
    if not account:
        logger.warning("Could not get account info for lot size calculation. Using default.")
        return config.DEFAULT_LOT_SIZE
        
    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        return config.DEFAULT_LOT_SIZE
        
    risk_amount = account.balance * (config.RISK_PERCENT / 100.0)
    
    # Distance in raw price
    price_distance = abs(entry_price - sl_price)
    if price_distance == 0:
        return config.DEFAULT_LOT_SIZE
        
    # How much we lose per 1 standard lot for this price distance
    # Tick value is profit/loss for 1 lot per tick_size change
    ticks = price_distance / symbol_info.trade_tick_size
    loss_per_lot = ticks * symbol_info.trade_tick_value
    
    if loss_per_lot == 0:
        return config.DEFAULT_LOT_SIZE
        
    lot_size = risk_amount / loss_per_lot
    
    # Constrain lot size to broker minimums and maximums
    if lot_size < symbol_info.volume_min:
        lot_size = symbol_info.volume_min
    elif lot_size > symbol_info.volume_max:
        lot_size = symbol_info.volume_max
        
    # Round to volume step
    step = symbol_info.volume_step
    lot_size = round(lot_size / step) * step
    
    return round(lot_size, 2)

def execute_trade(signal_data: dict) -> bool:
    """
    Executes the parsed trade signal on MetaTrader 5.
    Returns True if successful, False otherwise.
    """
    if not MT5_AVAILABLE:
        logger.info(f"MOCK EXECUTION: Trade signal valid -> {signal_data}")
        return True

    if not mt5.initialize(path=config.MT5_PATH, login=config.MT5_LOGIN, password=config.MT5_PASSWORD, server=config.MT5_SERVER):
        logger.error(f"MT5 initialization failed: {mt5.last_error()}")
        return False
        
    raw_symbol = signal_data['ticker']
    if getattr(config, 'AUTO_FIND_SYMBOL', True):
        mt5_symbol = resolve_symbol(raw_symbol)
    else:
        mt5_symbol = config.SYMBOL_MAPPING.get(raw_symbol, raw_symbol)
    
    # Check if symbol is available
    symbol_info = mt5.symbol_info(mt5_symbol)
    if symbol_info is None:
        logger.error(f"MT5: Symbol {mt5_symbol} not found.")
        return False
        
    if not symbol_info.visible:
        logger.info(f"MT5: Symbol {mt5_symbol} not visible, trying to select...")
        if not mt5.symbol_select(mt5_symbol, True):
            logger.error(f"MT5: Failed to select symbol {mt5_symbol}.")
            return False

    # Calculate TP and SL
    pip_val = config.PIP_VALUES.get(raw_symbol, 0.0001)
    tp, sl = calculate_tp_sl(
        entry_price=signal_data['entry_price'], 
        action=signal_data['action'], 
        target_pips=signal_data['target_pips'], 
        pip_value=pip_val, 
        sl_ratio=config.SL_RATIO
    )
    
    action = signal_data['action']
    order_type = mt5.ORDER_TYPE_BUY if action == ActionType.BUY else mt5.ORDER_TYPE_SELL
    
    # Refresh current prices (Market Execution vs Pending)
    # The requirement is immediate filling mode (Market Order)
    tick = mt5.symbol_info_tick(mt5_symbol)
    if not tick:
        logger.error(f"MT5: Failed to get tick for {mt5_symbol}")
        return False
        
    execution_price = tick.ask if action == ActionType.BUY else tick.bid

    volume = calculate_lot_size(mt5_symbol, sl, execution_price)

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": mt5_symbol,
        "volume": volume,
        "type": order_type,
        "price": execution_price,
        "sl": sl,
        "tp": tp,
        "deviation": config.MAX_SLIPPAGE,
        "magic": 1001,
        "comment": "TG Auto Bot",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    logger.info(f"MT5: Sending Order -> {request}")
    result = mt5.order_send(request)
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.error(f"MT5: Order failed. Retcode: {result.retcode}, Description: {result.comment}")
        # Depending on broker, sometimes FOK is required instead of IOC
        if result.retcode == mt5.TRADE_RETCODE_INVALID_FILL:
            logger.info("MT5: Retrying with ORDER_FILLING_FOK")
            request["type_filling"] = mt5.ORDER_FILLING_FOK
            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"MT5: Order failed again. Retcode: {result.retcode}")
                return False
        else:
            return False
            
    logger.info(f"MT5: Order EXECUTED successfully! Ticket: {result.order}")
    return True

# ==========================================
# MAIN ORCHESTRATOR
# ==========================================
db_conn = init_db()
client = TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH)

@client.on(events.NewMessage(chats=config.TARGET_CHANNEL_ID))
async def handle_new_message(event):
    message_id = event.message.id
    message_text = event.message.message
    
    if is_message_processed(db_conn, message_id):
        return
        
    logger.info(f"Received new message [{message_id}]")
    
    signal_data = parse_signal(message_text)
    if not signal_data:
        logger.debug(f"Message [{message_id}] is not a valid entry signal or is a target notification.")
        mark_message_processed(db_conn, message_id)
        return
        
    logger.info(f"Parsed Signal: {signal_data}")
    
    # Execute Trade
    success = execute_trade(signal_data)
    if success:
        logger.info(f"Trade for message [{message_id}] successfully dispatched.")
    else:
        logger.error(f"Trade for message [{message_id}] failed.")
        
    # Mark as processed regardless to avoid infinite retry loops on bad signals
    mark_message_processed(db_conn, message_id)


async def main():
    logger.info("Starting Telegram to MT5 Trading Bot...")
    # Initialize MT5 if available
    if MT5_AVAILABLE:
        if not mt5.initialize(path=config.MT5_PATH, login=config.MT5_LOGIN, password=config.MT5_PASSWORD, server=config.MT5_SERVER):
            logger.error(f"MT5 initialization failed: {mt5.last_error()}")
            logger.warning("Make sure you are on Windows or running MT5 correctly.")
        else:
            logger.info(f"Connected to MT5 terminal! Version: {mt5.version()}")
            
    # Start Telegram Client
    await client.start()
    logger.info(f"Listening for signals on channel ID: {config.TARGET_CHANNEL_ID}")
    
    # Run indefinitely
    await client.run_until_disconnected()

if __name__ == '__main__':
    try:
        # Check if running on non-Windows environment with MT5 imported
        import platform
        if platform.system() != 'Windows':
            logger.warning("You are running on a non-Windows OS! MT5 Python library natively requires Windows.")
            
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down bot gracefully...")
    finally:
        if MT5_AVAILABLE:
            mt5.shutdown()
        db_conn.close()
