#!/usr/bin/env python3
"""Interactive Telegram auth -- runs in a separate terminal window."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path


async def main() -> None:
    from telethon import TelegramClient
    from telethon.errors import SessionPasswordNeededError

    api_id = int(os.environ["TELEGRAM_API_ID"])
    api_hash = os.environ["TELEGRAM_API_HASH"]
    phone = os.environ["TELEGRAM_PHONE"]
    password = os.environ.get("TELEGRAM_PASSWORD")
    data_dir = Path(
        os.environ.get("TELEGRAM_DATA_DIR", str(Path.home() / ".better-telegram-mcp"))
    )
    session_name = os.environ.get("TELEGRAM_SESSION_NAME", "default")
    session_path = str(data_dir / session_name)

    print("=" * 50)
    print("  Telegram Authentication")
    print("=" * 50)
    print(f"\nOTP code has been sent to {phone}")
    print("Check your Telegram app on your phone.\n")

    client = TelegramClient(session_path, api_id, api_hash)
    await client.connect()

    try:
        code = input("Enter OTP code: ").strip()

        try:
            await client.sign_in(phone, code)
        except SessionPasswordNeededError:
            if password:
                print("Using 2FA password from TELEGRAM_PASSWORD env...")
                await client.sign_in(password=password)
            else:
                pwd = input("Enter 2FA password: ").strip()
                await client.sign_in(password=pwd)

        if await client.is_user_authorized():
            me = await client.get_me()
            name = getattr(me, "first_name", "")
            username = getattr(me, "username", None)
            username_part = f" (@{username})" if username else ""
            print(f"\nAuthenticated as: {name}{username_part}")
            sf = Path(session_path + ".session")
            if sf.exists():
                sf.chmod(0o600)
            print("Session saved. You can close this window.")
        else:
            print("Authentication failed!")
            sys.exit(1)
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
