import asyncio
from telethon import TelegramClient
import config

async def main():
    print("Connecting to Telegram...")
    # This will ask for your phone number and login code if it's the first time
    client = TelegramClient(config.SESSION_NAME, config.API_ID, config.API_HASH)
    await client.start()
    
    print("\n--- Your Recent Dialogs (Groups & Channels) ---")
    async for dialog in client.iter_dialogs():
        if dialog.is_channel or dialog.is_group:
            name_lower = dialog.name.lower() if dialog.name else ""
            if "safe" in name_lower or "gold" in name_lower:
                print(f"⭐ FOUND MATCH ⭐ Name: {dialog.name} | ID: {dialog.id}")
            else:
                print(f"Name: {dialog.name} | ID: {dialog.id}")
            
    print("\nCopy the exact ID of the target channel and paste it into config.py as TARGET_CHANNEL_ID.")
    await client.disconnect()
    
if __name__ == '__main__':
    asyncio.run(main())
