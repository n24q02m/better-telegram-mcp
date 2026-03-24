from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from loguru import logger
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from .backends.base import TelegramBackend
from .config import Settings
from .tools.chats import ChatOptions, handle_chats
from .tools.config_tool import handle_config
from .tools.contacts import ContactsOptions, handle_contacts
from .tools.help_tool import handle_help
from .tools.media import MediaOptions, handle_media
from .tools.messages import handle_messages
from .utils.formatting import err, ok


class MessagesArgs(BaseModel):
    action: str = Field(description="send|edit|delete|forward|pin|react|search|history")
    chat_id: str | int | None = None
    text: str | None = None
    message_id: int | None = None
    reply_to: int | None = None
    parse_mode: str | None = None
    from_chat: str | int | None = None
    to_chat: str | int | None = None
    emoji: str | None = None
    query: str | None = None
    limit: int = 20
    offset_id: int | None = None


_backend: TelegramBackend | None = None
_settings: Settings | None = None
_pending_auth: bool = False
_unconfigured: bool = False
_auth_url: str | None = None
_runtime_config: dict[str, int] = {
    "message_limit": 20,
    "timeout": 30,
}


def get_backend() -> TelegramBackend:
    if _backend is None:
        msg = "Backend not initialized. Server lifespan not started."
        raise RuntimeError(msg)
    return _backend


def get_settings() -> Settings:
    if _settings is None:
        msg = "Settings not initialized. Server lifespan not started."
        raise RuntimeError(msg)
    return _settings


def _not_ready_response() -> str:
    if _unconfigured:
        return ok(
            {
                "error": "Not configured",
                "setup": {
                    "bot_mode": {
                        "env_var": "TELEGRAM_BOT_TOKEN",
                        "how": "Get token from @BotFather on Telegram",
                        "example": "TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
                    },
                    "user_mode": {
                        "env_vars": [
                            "TELEGRAM_API_ID",
                            "TELEGRAM_API_HASH",
                            "TELEGRAM_PHONE",
                        ],
                        "how": "Get API credentials from https://my.telegram.org",
                        "example": "TELEGRAM_API_ID=12345 TELEGRAM_API_HASH=abcdef... TELEGRAM_PHONE=+84912345678",
                    },
                },
            }
        )
    if _auth_url:
        return err(
            f"Telegram session not authenticated. "
            f"Open {_auth_url} in your browser to authenticate."
        )
    return err(
        "Telegram session not authenticated and TELEGRAM_PHONE not configured. "
        "Set TELEGRAM_PHONE in your MCP server env config, then restart."
    )


async def _start_auth(
    backend: TelegramBackend, settings: Settings
) -> tuple[object, str]:
    """Start auth flow (local or remote). Returns (handler, auth_url)."""
    if settings.auth_url == "local":
        from .auth_server import AuthServer

        srv = AuthServer(backend, settings)
        url = await srv.start()
        return srv, url
    else:
        from .auth_client import AuthClient

        client = AuthClient(backend, settings)
        url = await client.create_session()
        return client, url


async def _run_auth_background(handler: object) -> None:
    """Run auth polling/waiting in background."""
    global _pending_auth

    from .auth_client import AuthClient
    from .auth_server import AuthServer

    if isinstance(handler, AuthClient):
        # Remote mode: poll relay server and execute commands locally
        await handler.poll_and_execute()
        await handler.wait_for_auth()
    elif isinstance(handler, AuthServer):
        # Local mode: wait for auth completion via localhost web server
        await handler.wait_for_auth()

    _pending_auth = False
    logger.info("Authentication completed!")


async def _stop_auth(handler: object) -> None:
    """Clean up auth handler."""
    from .auth_client import AuthClient
    from .auth_server import AuthServer

    if isinstance(handler, AuthClient):
        await handler.close()
    elif isinstance(handler, AuthServer):
        await handler.stop()


@asynccontextmanager
async def _lifespan(server: FastMCP) -> AsyncIterator[None]:
    global _backend, _settings, _pending_auth, _unconfigured, _auth_url
    _settings = Settings()

    if not _settings.is_configured:
        _unconfigured = True
        logger.warning(
            "No Telegram credentials configured. "
            "help and config tools available; other tools will show setup instructions. "
            "Set TELEGRAM_BOT_TOKEN or TELEGRAM_API_ID + TELEGRAM_API_HASH to enable all tools."
        )
        try:
            yield
        finally:
            _unconfigured = False
        return

    logger.info("Mode: {}", _settings.mode)

    if _settings.mode == "bot":
        from .backends.bot_backend import BotBackend

        assert _settings.bot_token is not None
        _backend = BotBackend(_settings.bot_token)
    else:
        from .backends.user_backend import UserBackend

        assert _settings.api_id is not None
        assert _settings.api_hash is not None
        _backend = UserBackend(_settings)

    await _backend.connect()
    logger.info("Connected to Telegram ({})", _settings.mode)

    auth_handler = None
    if _settings.mode == "user" and not await _backend.is_authorized():
        if _settings.phone:
            _pending_auth = True
            auth_handler, _auth_url = await _start_auth(_backend, _settings)
            logger.warning(
                "Session not authorized. Open {} to authenticate.", _auth_url
            )

            import webbrowser

            def _open_browser() -> None:
                try:
                    # Bolt: webbrowser.open() is a synchronous, blocking call that invokes an external GUI process.
                    # Offloading it to a separate thread as a background task prevents blocking the async event loop
                    # AND avoids blocking the _lifespan generator, ensuring the MCP server starts instantly.
                    webbrowser.open(_auth_url)
                except Exception:
                    pass

            asyncio.create_task(asyncio.to_thread(_open_browser))

            asyncio.create_task(_run_auth_background(auth_handler))
        else:
            _pending_auth = True
            logger.warning(
                "Session not authorized and TELEGRAM_PHONE not set. "
                "Set TELEGRAM_PHONE in your MCP server config, then restart."
            )

    try:
        yield
    finally:
        if auth_handler is not None:
            await _stop_auth(auth_handler)
        _auth_url = None
        await _backend.disconnect()
        logger.info("Disconnected from Telegram")


mcp = FastMCP(
    "better-telegram-mcp",
    lifespan=_lifespan,
)


# --- Tools ---


@mcp.tool(
    annotations=ToolAnnotations(
        title="Telegram Messages",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=True,
    )
)
async def messages(args: MessagesArgs) -> str:
    """Send, search, and manage Telegram messages.

    Actions (required params -> optional):
    - send (chat_id, text -> reply_to, parse_mode)
    - edit (chat_id, message_id, text -> parse_mode)
    - delete (chat_id, message_id)
    - forward (from_chat, to_chat, message_id)
    - pin (chat_id, message_id)
    - react (chat_id, message_id, emoji)
    - search (query -> chat_id, limit=20)
    - history (chat_id -> limit=20, offset_id)

    chat_id: "@username" | 123456789 | -1001234567890
    parse_mode: "HTML" | "MarkdownV2" | "Markdown" (default: plain text)
    """
    if _unconfigured or _pending_auth:
        return _not_ready_response()
    return await handle_messages(get_backend(), args)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Telegram Chats",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=True,
    )
)
async def chats(
    action: str,
    options: ChatOptions | None = None,
) -> str:
    """List, create, and manage Telegram chats, groups, and channels.

    Actions (required params -> optional):
    - list (-> limit=50)
    - info (chat_id)
    - create (title -> is_channel)
    - join (link_or_hash)
    - leave (chat_id)
    - members (chat_id -> limit=50)
    - admin (chat_id, user_id -> demote)
    - settings (chat_id, title|description)
    - topics (chat_id, topic_action -> topic_id, topic_name)

    chat_id: "@username" | 123456789 | -1001234567890
    Tip: Use 'list' first to discover chat IDs."""
    if _unconfigured or _pending_auth:
        return _not_ready_response()

    opts = options if options is not None else ChatOptions()
    return await handle_chats(
        get_backend(),
        action,
        opts,
    )


@mcp.tool(
    annotations=ToolAnnotations(
        title="Telegram Media",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    )
)
async def media(
    action: str,
    chat_id: str | int | None = None,
    file_path_or_url: str | None = None,
    message_id: int | None = None,
    caption: str | None = None,
    output_dir: str | None = None,
) -> str:
    """Send and download media files in Telegram chats.

    Actions (required params -> optional):
    - send_photo (chat_id, file_path_or_url -> caption): JPEG/PNG/WebP, max 10MB
    - send_file (chat_id, file_path_or_url -> caption): any type, max 50MB
    - send_voice (chat_id, file_path_or_url -> caption): OGG/OPUS, max 50MB
    - send_video (chat_id, file_path_or_url -> caption): MP4, max 50MB
    - download (chat_id, message_id -> output_dir): save media from message

    file_path_or_url: local path ("/tmp/photo.jpg") or URL ("https://...")
    chat_id: "@username" | 123456789 | -1001234567890"""
    if _unconfigured or _pending_auth:
        return _not_ready_response()
    return await handle_media(
        get_backend(),
        action,
        MediaOptions(
            chat_id=chat_id,
            file_path_or_url=file_path_or_url,
            message_id=message_id,
            caption=caption,
            output_dir=output_dir,
        ),
    )


@mcp.tool(
    annotations=ToolAnnotations(
        title="Telegram Contacts",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=False,
    )
)
async def contacts(
    action: str,
    query: str | None = None,
    phone: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    user_id: int | None = None,
    unblock: bool = False,
) -> str:
    """Manage Telegram contacts (user mode only, not available in bot mode).

    Actions (required params -> optional):
    - list: Show all contacts
    - search (query): Find contacts by name
    - add (phone, first_name -> last_name): Add new contact
    - block (user_id -> unblock=true): Block or unblock a user"""
    if _unconfigured or _pending_auth:
        return _not_ready_response()

    opts = ContactsOptions(
        query=query,
        phone=phone,
        first_name=first_name,
        last_name=last_name,
        user_id=user_id,
        unblock=unblock,
    )
    return await handle_contacts(
        get_backend(),
        action,
        options=opts,
    )


@mcp.tool(
    annotations=ToolAnnotations(
        title="Telegram Config",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
async def config(
    action: str,
    message_limit: int | None = None,
    timeout: int | None = None,
) -> str:
    """Server configuration and runtime settings.

    Actions (required params):
    - status: Show connection state, mode, and current config
    - set (message_limit|timeout): Update runtime limits
    - cache_clear: Clear internal caches"""
    if _unconfigured:
        if action == "status":
            return ok(
                {
                    "mode": None,
                    "connected": False,
                    "authorized": False,
                    "configured": False,
                    "config": _runtime_config,
                    "setup": {
                        "bot_mode": "Set TELEGRAM_BOT_TOKEN (get from @BotFather)",
                        "user_mode": "Set TELEGRAM_API_ID + TELEGRAM_API_HASH + TELEGRAM_PHONE (from my.telegram.org)",
                    },
                }
            )
        return _not_ready_response()
    return await handle_config(
        get_backend(),
        action,
        message_limit=message_limit,
        timeout=timeout,
    )


@mcp.tool(
    annotations=ToolAnnotations(
        title="Telegram Help",
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
async def help(topic: str | None = None) -> str:
    """Get full documentation for any tool. Use when compressed descriptions are insufficient.

    Topics: messages | chats | media | contacts | all (default: all)"""
    return await handle_help(topic)


# --- Resources ---
from .resources import register_resources  # noqa: E402

register_resources(mcp)


def main() -> None:
    mcp.run(transport="stdio")
