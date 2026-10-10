# Trade Signal Executor

An event-driven bridge that listens to Telegram channels and executes trades on MetaTrader 5 with automated risk calculations and broker symbol resolution.

## Overview

Manual trade execution from signal channels introduces latency and calculation errors. This application runs an asynchronous MTProto client using Telethon, parses incoming signals with regular expressions, computes position sizing based on account equity, and sends market orders directly to a local MetaTrader 5 terminal.

## Key Features

- Asynchronous message consumption from private Telegram channels.
- Configurable risk management calculating lot sizes from account balance and tick metrics.
- SQLite-backed state tracking preventing duplicate order executions.
- Automatic symbol normalization for broker-specific suffixes.
- Take-profit and stop-loss calculation based on target pip ratios.

## System Architecture

1. Message Ingestion: Telethon listens for new messages on configured channel IDs.
2. Deduplication: Message IDs are checked against an internal SQLite database.
3. Parsing: Extraction logic identifies ticker, entry direction, price, and target pips.
4. Risk Computation: Queries MT5 for balance, tick size, and tick value to determine volume.
5. Order Dispatch: Submits market order with defined stop-loss and take-profit parameters.

## Prerequisites

- Windows 10/11 or Windows Server (MetaTrader 5 Python bridge requirement).
- MetaTrader 5 desktop client installed and logged into an active broker account.
- Python 3.10 or higher.
- Telegram API credentials (API ID and API Hash from my.telegram.org).

## Installation

```bash
git clone https://github.com/your-username/trade-signal-executor.git
cd trade-signal-executor
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and provide your credentials:

```env
TELEGRAM_API_ID=1234567
TELEGRAM_API_HASH=your_api_hash_here
TARGET_CHANNEL_ID=-1001234567890
RISK_PERCENT=2.0
DEFAULT_LOT_SIZE=0.01
```

## Usage

```bash
python main.py
```

On first launch, Telethon will prompt for your phone number to generate an authorized session file.

## Testing

Run parser unit tests:

```bash
python -m unittest discover -s tests
```

## License

MIT
