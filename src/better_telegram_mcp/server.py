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
    backend: TelegramBackend,
    settings: Settings,
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

    # If env vars not set, try relay config (config file -> relay setup)
    relay_config = None
    if not _settings.is_configured:
        from .relay_setup import ensure_config

        relay_config = await ensure_config()
        if relay_config:
            _settings = Settings.from_relay_config(relay_config)

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
        if _settings.phone and relay_config is None:
            # Only start separate auth flow if NOT coming from relay setup
            # (relay_setup.py handles OTP/2FA via bidirectional messaging)
            _pending_auth = True
            auth_handler, _auth_url = await _start_auth(_backend, _settings)
            logger.warning(
                "Session not authorized. Open {} to authenticate.", _auth_url
            )

            import webbrowser

            def _open_browser() -> None:
                try:
                    # Bolt: webbrowser.open() is a synchronous, blocking call
                    # that invokes an external GUI process.
                    # Offloading it to a separate thread as a background task
                    # prevents blocking the async event loop AND avoids blocking
                    # the _lifespan generator, ensuring the MCP server starts
                    # instantly.
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


# --- Action-to-domain mapping for the unified telegram tool ---

# Messages domain: actions handled by tools/messages.py
_MESSAGES_ACTIONS = {
    "send",
    "edit",
    "delete",
    "forward",
    "pin",
    "react",
    "search",
    "history",
}

# Chats domain: action name -> chats handler action name
_CHATS_ACTION_MAP = {
    "list_chats": "list",
    "chat_info": "info",
    "create_chat": "create",
    "join_chat": "join",
    "leave_chat": "leave",
    "chat_members": "members",
    "chat_admin": "admin",
    "chat_settings": "settings",
    "chat_topics": "topics",
}

# Media domain: actions handled by tools/media.py
_MEDIA_ACTIONS = {
    "send_photo",
    "send_file",
    "send_voice",
    "send_video",
    "download_media",
}

# Media action name -> media handler action name
_MEDIA_ACTION_MAP = {
    "download_media": "download",
}

# Contacts domain: action name -> contacts handler action name
_CONTACTS_ACTION_MAP = {
    "list_contacts": "list",
    "search_contacts": "search",
    "add_contact": "add",
    "block_user": "block",
}

# All valid actions for error messages
_ALL_ACTIONS = sorted(
    [*_MESSAGES_ACTIONS, *_CHATS_ACTION_MAP, *_MEDIA_ACTIONS, *_CONTACTS_ACTION_MAP]
)


# --- Tools ---


@mcp.tool(
    annotations=ToolAnnotations(
        title="Telegram",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=True,
    )
)
async def telegram(
    action: str,
    # Messages params
    chat_id: str | int | None = None,
    text: str | None = None,
    message_id: int | None = None,
    reply_to: int | None = None,
    parse_mode: str | None = None,
    from_chat: str | int | None = None,
    to_chat: str | int | None = None,
    emoji: str | None = None,
    query: str | None = None,
    limit: int | None = None,
    offset_id: int | None = None,
    # Chats params
    title: str | None = None,
    description: str | None = None,
    is_channel: bool = False,
    link_or_hash: str | None = None,
    user_id: int | None = None,
    demote: bool = False,
    topic_action: str | None = None,
    topic_id: int | None = None,
    topic_name: str | None = None,
    # Media params
    file_path_or_url: str | None = None,
    caption: str | None = None,
    output_dir: str | None = None,
    # Contacts params
    phone: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    unblock: bool = False,
) -> str:
    """Send messages, manage chats, transfer media, and handle contacts.

    MESSAGE actions (chat_id: "@username" | int):
    - send (chat_id, text -> reply_to, parse_mode)
    - edit (chat_id, message_id, text -> parse_mode)
    - delete (chat_id, message_id)
    - forward (from_chat, to_chat, message_id)
    - pin (chat_id, message_id)
    - react (chat_id, message_id, emoji)
    - search (query -> chat_id, limit=20)
    - history (chat_id -> limit=20, offset_id)

    CHAT actions:
    - list_chats (-> limit=50)
    - chat_info (chat_id)
    - create_chat (title -> is_channel)
    - join_chat (link_or_hash)
    - leave_chat (chat_id)
    - chat_members (chat_id -> limit=50)
    - chat_admin (chat_id, user_id -> demote)
    - chat_settings (chat_id, title|description)
    - chat_topics (chat_id, topic_action -> topic_id, topic_name)

    MEDIA actions (file_path_or_url: local path or URL):
    - send_photo (chat_id, file_path_or_url -> caption)
    - send_file (chat_id, file_path_or_url -> caption)
    - send_voice (chat_id, file_path_or_url -> caption)
    - send_video (chat_id, file_path_or_url -> caption)
    - download_media (chat_id, message_id -> output_dir)

    CONTACT actions (user mode only):
    - list_contacts: Show all contacts
    - search_contacts (query): Find contacts by name
    - add_contact (phone, first_name -> last_name)
    - block_user (user_id -> unblock=true)
    """
    if _unconfigured or _pending_auth:
        return _not_ready_response()

    backend = get_backend()

    # --- Messages domain ---
    if action in _MESSAGES_ACTIONS:
        args = MessagesArgs(
            action=action,
            chat_id=chat_id,
            text=text,
            message_id=message_id,
            reply_to=reply_to,
            parse_mode=parse_mode,
            from_chat=from_chat,
            to_chat=to_chat,
            emoji=emoji,
            query=query,
            limit=limit if limit is not None else 20,
            offset_id=offset_id,
        )
        return await handle_messages(backend, args)

    # --- Chats domain ---
    if action in _CHATS_ACTION_MAP:
        chats_action = _CHATS_ACTION_MAP[action]
        opts = ChatOptions(
            chat_id=chat_id,
            title=title,
            description=description,
            is_channel=is_channel,
            link_or_hash=link_or_hash,
            user_id=user_id,
            demote=demote,
            limit=limit if limit is not None else 50,
            topic_action=topic_action,
            topic_id=topic_id,
            topic_name=topic_name,
        )
        return await handle_chats(backend, chats_action, opts)

    # --- Media domain ---
    if action in _MEDIA_ACTIONS:
        media_action = _MEDIA_ACTION_MAP.get(action, action)
        opts = MediaOptions(
            chat_id=chat_id,
            file_path_or_url=file_path_or_url,
            message_id=message_id,
            caption=caption,
            output_dir=output_dir,
        )
        return await handle_media(backend, media_action, opts)

    # --- Contacts domain ---
    if action in _CONTACTS_ACTION_MAP:
        contacts_action = _CONTACTS_ACTION_MAP[action]
        opts = ContactsOptions(
            query=query,
            phone=phone,
            first_name=first_name,
            last_name=last_name,
            user_id=user_id,
            unblock=unblock,
        )
        return await handle_contacts(backend, contacts_action, options=opts)

    # --- Unknown action ---
    import difflib

    closest = difflib.get_close_matches(action, _ALL_ACTIONS, n=1)
    suggestion = f" Did you mean '{closest[0]}'?" if closest else ""
    return err(
        f"Unknown action '{action}'.{suggestion} Valid: {'|'.join(_ALL_ACTIONS)}"
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
