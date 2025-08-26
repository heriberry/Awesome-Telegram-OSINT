#!/usr/bin/env python3
"""Basic Telegram OSINT script using Telethon.

This script retrieves information about a Telegram entity (user, chat, or channel)
and optionally fetches a limited number of recent messages.

Environment variables:
    TELEGRAM_API_ID: Telegram API ID
    TELEGRAM_API_HASH: Telegram API hash

Usage:
    python telegram_osint.py --entity <username_or_id> [--limit N]
"""

import argparse
import asyncio
import json
import os
import sys
from typing import Any, Dict

from telethon import TelegramClient
from telethon.errors import RPCError
from telethon.tl.functions.channels import GetFullChannelRequest


async def fetch_entity_info(client: TelegramClient, entity: str, limit: int) -> Dict[str, Any]:
    """Fetch basic information and recent messages for a given Telegram entity."""
    try:
        resolved = await client.get_entity(entity)
        result = {"id": resolved.id, "type": type(resolved).__name__}

        if hasattr(resolved, "title"):
            result["title"] = resolved.title
        if hasattr(resolved, "username"):
            result["username"] = resolved.username

        try:
            full = await client(GetFullChannelRequest(resolved))
            participants = full.full_chat.participants_count
            result["participants"] = participants
        except RPCError:
            pass

        messages = []
        async for message in client.iter_messages(resolved, limit=limit):
            messages.append({"id": message.id, "date": message.date.isoformat(), "text": message.message})
        result["messages"] = messages
        return result
    except RPCError as err:
        raise RuntimeError(f"Failed to fetch entity info: {err}") from err


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect basic information about a Telegram entity")
    parser.add_argument("--entity", required=True, help="Username or ID of the target entity")
    parser.add_argument("--limit", type=int, default=10, help="Number of recent messages to retrieve")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    try:
        api_id = int(os.environ["TELEGRAM_API_ID"])
        api_hash = os.environ["TELEGRAM_API_HASH"]
    except KeyError as err:
        missing = err.args[0]
        print(f"Missing required environment variable: {missing}", file=sys.stderr)
        sys.exit(1)

    async with TelegramClient("osint_session", api_id, api_hash) as client:
        info = await fetch_entity_info(client, args.entity, args.limit)
        print(json.dumps(info, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
