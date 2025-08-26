"""Example Telegram OSINT script using Telethon.

Set the environment variables TG_API_ID, TG_API_HASH, and TG_CHANNEL
before running. The script prints the last ten messages from the
specified channel.
"""

import os
import asyncio
from telethon import TelegramClient

API_ID = int(os.environ.get("TG_API_ID", "0"))
API_HASH = os.environ.get("TG_API_HASH", "")
CHANNEL = os.environ.get("TG_CHANNEL", "telegram")


async def main() -> None:
    if not API_ID or not API_HASH:
        raise RuntimeError("TG_API_ID and TG_API_HASH must be set")
    async with TelegramClient("osint_session", API_ID, API_HASH) as client:
        async for message in client.iter_messages(CHANNEL, limit=10):
            print(f"{message.id}: {message.text}")


if __name__ == "__main__":
    asyncio.run(main())
