from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from loguru import logger
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .backends.base import TelegramBackend
from .config import Settings
from .tools.chats import handle_chats
from .tools.config_tool import handle_config
from .tools.contacts import handle_contacts
from .tools.help_tool import handle_help
from .tools.media import handle_media
from .tools.messages import handle_messages
from .utils.formatting import err

_backend: TelegramBackend | None = None
_settings: Settings | None = None
_pending_auth: bool = False
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


def _auth_required_response() -> str:
    return err(
        "Authentication required. OTP code has been sent to your Telegram app. "
        "Use: config(action='auth', code='YOUR_CODE') to complete authentication."
    )


def _auth_missing_phone_response() -> str:
    return err(
        "User mode requires TELEGRAM_PHONE env var for automatic auth. "
        "Set it in your MCP config alongside TELEGRAM_API_ID and TELEGRAM_API_HASH."
    )


@asynccontextmanager
async def _lifespan(server: FastMCP) -> AsyncIterator[None]:
    global _backend, _settings, _pending_auth
    _settings = Settings()
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

    # Auto-auth flow for user mode
    if _settings.mode == "user" and not await _backend.is_authorized():
        if _settings.phone:
            logger.info("Session not authorized. Sending OTP to {}...", _settings.phone)
            await _backend.send_code(_settings.phone)
            _pending_auth = True
            logger.info("OTP sent. Waiting for auth via config tool.")
        else:
            logger.warning(
                "Session not authorized and TELEGRAM_PHONE not set. "
                "Auth will need to be initiated via config(action='send_code')."
            )
            _pending_auth = True

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
async def messages(
    action: str,
    chat_id: str | int | None = None,
    text: str | None = None,
    message_id: int | None = None,
    reply_to: int | None = None,
    parse_mode: str | None = None,
    from_chat: str | int | None = None,
    to_chat: str | int | None = None,
    emoji: str | None = None,
    query: str | None = None,
    limit: int = 20,
    offset_id: int | None = None,
) -> str:
    """send|edit|delete|forward|pin|react|search|history"""
    if _pending_auth:
        return _auth_required_response()
    return await handle_messages(
        get_backend(),
        action,
        chat_id=chat_id,
        text=text,
        message_id=message_id,
        reply_to=reply_to,
        parse_mode=parse_mode,
        from_chat=from_chat,
        to_chat=to_chat,
        emoji=emoji,
        query=query,
        limit=limit,
        offset_id=offset_id,
    )


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
    chat_id: str | int | None = None,
    title: str | None = None,
    description: str | None = None,
    is_channel: bool = False,
    link_or_hash: str | None = None,
    user_id: int | None = None,
    demote: bool = False,
    limit: int = 50,
    topic_action: str | None = None,
    topic_id: int | None = None,
    topic_name: str | None = None,
) -> str:
    """list|info|create|join|leave|members|admin|settings|topics"""
    if _pending_auth:
        return _auth_required_response()
    return await handle_chats(
        get_backend(),
        action,
        chat_id=chat_id,
        title=title,
        description=description,
        is_channel=is_channel,
        link_or_hash=link_or_hash,
        user_id=user_id,
        demote=demote,
        limit=limit,
        topic_action=topic_action,
        topic_id=topic_id,
        topic_name=topic_name,
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
    """send_photo|send_file|send_voice|send_video|download"""
    if _pending_auth:
        return _auth_required_response()
    return await handle_media(
        get_backend(),
        action,
        chat_id=chat_id,
        file_path_or_url=file_path_or_url,
        message_id=message_id,
        caption=caption,
        output_dir=output_dir,
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
    """list|search|add|block (user mode only)"""
    if _pending_auth:
        return _auth_required_response()
    return await handle_contacts(
        get_backend(),
        action,
        query=query,
        phone=phone,
        first_name=first_name,
        last_name=last_name,
        user_id=user_id,
        unblock=unblock,
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
    code: str | None = None,
    message_limit: int | None = None,
    timeout: int | None = None,
) -> str:
    """status|set|cache_clear|auth|send_code"""
    return await handle_config(
        get_backend(),
        action,
        code=code,
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
    """Full documentation. Topics: messages|chats|media|contacts|all"""
    return handle_help(topic)


# --- Resources ---
from .resources import register_resources  # noqa: E402

register_resources(mcp)


def main() -> None:
    mcp.run(transport="stdio")
