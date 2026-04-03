from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from loguru import logger
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .backends.base import TelegramBackend
from .config import Settings
from .tools.chats import ChatOptions, handle_chats
from .tools.config_tool import handle_config
from .tools.contacts import ContactsOptions, handle_contacts
from .tools.help_tool import handle_help
from .tools.media import MediaOptions, handle_media
from .tools.messages import MessagesArgs, handle_messages
from .utils.formatting import err, ok

_backend: TelegramBackend | None = None
_settings: Settings | None = None
_pending_auth: bool = False
_unconfigured: bool = False
_runtime_config: dict[str, int] = {
    "message_limit": 20,
    "timeout": 30,
}

# Track whether we're in multi-user HTTP mode
_multi_user_mode: bool = False


def get_backend() -> TelegramBackend:
    """Get the active backend.

    In multi-user HTTP mode: returns the per-user backend from ContextVar.
    In stdio/single-user mode: returns the global _backend.
    """
    if _multi_user_mode:
        from .transports.http import get_current_backend

        backend = get_current_backend()
        if backend is not None:
            return backend

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
                        "env_vars": ["TELEGRAM_PHONE"],
                        "how": "Set your phone number (API credentials have built-in defaults)",
                        "example": "TELEGRAM_PHONE=+84912345678",
                        "optional_overrides": ["TELEGRAM_API_ID", "TELEGRAM_API_HASH"],
                    },
                },
            }
        )
    return err(
        "Telegram session not authenticated. "
        "Remove credential env vars and restart to trigger relay setup, "
        "or set TELEGRAM_PHONE in your MCP server env config."
    )


@asynccontextmanager
async def _lifespan(server: FastMCP) -> AsyncIterator[None]:
    global _backend, _settings, _pending_auth, _unconfigured
    _settings = Settings()

    # If env vars not set, try relay config (config file -> relay setup)
    relay_config = None
    if not _settings.is_configured:
        from .relay_setup import ensure_config

        relay_config = await ensure_config()
        if relay_config:
            _settings = Settings.from_relay_config(relay_config)

    if not _settings.is_configured:
        if _multi_user_mode:
            # Multi-user HTTP mode: per-user backends injected via ContextVar.
            # No global backend needed — skip unconfigured state.
            logger.info("Multi-user HTTP mode: per-user backends via bearer auth.")
            try:
                yield
            finally:
                pass
            return

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

    if _settings.mode == "user" and not await _backend.is_authorized():
        _pending_auth = True
        logger.warning(
            "Session not authorized. "
            "Remove credential env vars and restart to trigger relay setup "
            "(relay handles OTP/2FA via bidirectional messaging)."
        )

    try:
        yield
    finally:
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
async def message(args: MessagesArgs) -> str:
    """Send, edit, delete, forward, pin, react, search, and get message history.

    Actions (chat_id: "@username" | int):
    - send (chat_id, text -> reply_to, parse_mode)
    - edit (chat_id, message_id, text -> parse_mode)
    - delete (chat_id, message_id)
    - forward (from_chat, to_chat, message_id)
    - pin (chat_id, message_id)
    - react (chat_id, message_id, emoji)
    - search (query -> chat_id, limit=20)
    - history (chat_id -> limit=20, offset_id)
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
async def chat(args: ChatOptions) -> str:
    """List, create, join, leave, manage members, settings, and topics.

    Actions:
    - list (-> limit=50)
    - info (chat_id)
    - create (title -> is_channel)
    - join (link_or_hash)
    - leave (chat_id)
    - members (chat_id -> limit=50)
    - admin (chat_id, user_id -> demote)
    - settings (chat_id, title|description)
    - topics (chat_id, topic_action -> topic_id, topic_name)
    """
    if _unconfigured or _pending_auth:
        return _not_ready_response()

    return await handle_chats(get_backend(), args)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Telegram Media",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    )
)
async def media(args: MediaOptions) -> str:
    """Send photos, files, voice, video, and download media from messages.

    Actions (file_path_or_url: local path or URL):
    - send_photo (chat_id, file_path_or_url -> caption)
    - send_file (chat_id, file_path_or_url -> caption)
    - send_voice (chat_id, file_path_or_url -> caption)
    - send_video (chat_id, file_path_or_url -> caption)
    - download (chat_id, message_id -> output_dir)
    """
    if _unconfigured or _pending_auth:
        return _not_ready_response()

    return await handle_media(get_backend(), args)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Telegram Contacts",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    )
)
async def contact(args: ContactsOptions) -> str:
    """Manage contacts: list, search, add, and block/unblock users (user mode only).

    Actions:
    - list: Show all contacts
    - search (query): Find contacts by name
    - add (phone, first_name -> last_name)
    - block (user_id -> unblock=true)
    """
    if _unconfigured or _pending_auth:
        return _not_ready_response()

    return await handle_contacts(get_backend(), args)


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
    - cache_clear: Clear internal caches
    """
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
                        "user_mode": (
                            "Set TELEGRAM_PHONE"
                            " (API credentials have built-in defaults)"
                        ),
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
    """Get full documentation for any topic.

    Topics: telegram | messages | chats | media | contacts | all (default: all)
    """
    return await handle_help(topic)


# --- Resources ---
from .resources import register_resources  # noqa: E402

register_resources(mcp)


def create_http_mcp_server() -> FastMCP:
    """Create a FastMCP server instance for multi-user HTTP mode.

    Returns the existing mcp instance (tools are shared across sessions).
    Per-user backend is injected via ContextVar per request.
    """
    global _multi_user_mode
    _multi_user_mode = True
    return mcp


def main() -> None:
    import os

    transport = os.environ.get("TRANSPORT_MODE", "stdio")
    if transport == "http":
        from .transports.http import start_http

        start_http(Settings())
    else:
        mcp.run(transport="stdio")
