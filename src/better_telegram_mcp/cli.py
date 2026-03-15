from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from telethon import TelegramClient


async def _auth_async(session_name: str | None = None) -> None:
    api_id = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")
    phone = os.environ.get("TELEGRAM_PHONE")
    password = os.environ.get("TELEGRAM_PASSWORD")

    if not api_id or not api_hash:
        print("Error: Set TELEGRAM_API_ID and TELEGRAM_API_HASH environment variables.")
        print("Get them from https://my.telegram.org")
        sys.exit(1)

    data_dir = Path(
        os.environ.get("TELEGRAM_DATA_DIR", Path.home() / ".better-telegram-mcp")
    )
    data_dir.mkdir(parents=True, exist_ok=True)

    name = session_name or os.environ.get("TELEGRAM_SESSION_NAME", "default")
    session_path = data_dir / name

    print(f"Authenticating Telegram (session: {session_path})...")

    client = TelegramClient(str(session_path), int(api_id), api_hash)
    await client.connect()

    if not await client.is_user_authorized():
        if not phone:
            phone = input("Phone number (e.g., +84912345678): ")

        await client.send_code_request(phone)
        code = input("Enter the code you received: ")

        try:
            await client.sign_in(phone, code)
        except Exception:
            if password:
                await client.sign_in(password=password)
            else:
                pwd = input("2FA password: ")
                await client.sign_in(password=pwd)

    me = await client.get_me()
    print(f"Authenticated as: {me.first_name} (@{me.username})")

    session_file = session_path.with_suffix(".session")
    if session_file.exists():
        session_file.chmod(0o600)
        print(f"Session saved: {session_file} (permissions: 600)")

    await client.disconnect()
    print("Auth complete. You can now use better-telegram-mcp in MCP config.")


def run_auth() -> None:
    parser = argparse.ArgumentParser(description="Authenticate Telegram")
    parser.add_argument(
        "--session-name",
        default=None,
        help="Session name (default: from env or 'default')",
    )
    # Parse only known args to avoid conflict with __main__.py
    args, _ = parser.parse_known_args(sys.argv[2:])
    asyncio.run(_auth_async(args.session_name))
