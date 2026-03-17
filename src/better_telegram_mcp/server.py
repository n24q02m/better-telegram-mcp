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
from .tools.contacts import ContactsArgs, handle_contacts
from .tools.help_tool import handle_help
from .tools.media import handle_media
from .tools.messages import handle_messages
from .utils.formatting import err


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


def _auth_required_response() -> str:
    if _auth_url:
        return err(
            f"Telegram session not authenticated. "
            f"Open {_auth_url} in your browser to complete authentication. "
            f"Headless? Use: curl -X POST {_auth_url}/send-code && "
            f"curl -X POST {_auth_url}/verify -H 'Content-Type: application/json' "
            f'-d \'{{"code":"YOUR_OTP"}}\''
        )
    return err(
        "Telegram session not authenticated and TELEGRAM_PHONE not configured. "
        "Set TELEGRAM_PHONE in your MCP server env config, then restart."
    )


@asynccontextmanager
async def _lifespan(server: FastMCP) -> AsyncIterator[None]:
    global _backend, _settings, _pending_auth, _auth_url
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

    auth_srv = None
    if _settings.mode == "user" and not await _backend.is_authorized():
        _pending_auth = True

        if _settings.phone:
            from .auth_server import AuthServer

            auth_srv = AuthServer(_backend, _settings)
            _auth_url = await auth_srv.start()
            logger.warning(
                "Session not authorized. Open {} to authenticate.", _auth_url
            )

            # Try to open browser automatically
            import webbrowser

            try:
                webbrowser.open(_auth_url)
            except Exception:
                pass  # User can open URL manually from log/error message
        else:
            logger.warning(
                "Session not authorized and TELEGRAM_PHONE not set. "
                "Set TELEGRAM_PHONE in your MCP server config, then restart."
            )

    try:
        # If auth server is running, wait for auth in background
        if auth_srv is not None:

            async def _wait_auth() -> None:
                global _pending_auth, _auth_url
                await auth_srv.wait_for_auth()
                _pending_auth = False
                _auth_url = None
                logger.info("Authentication completed via web UI!")
                await auth_srv.stop()

            asyncio.create_task(_wait_auth())

        yield
    finally:
        if auth_srv is not None:
            await auth_srv.stop()
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
    """send|edit|delete|forward|pin|react|search|history"""
    if _pending_auth:
        return _auth_required_response()
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
    """list|info|create|join|leave|members|admin|settings|topics"""
    if _pending_auth:
        return _auth_required_response()

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
    args = ContactsArgs(
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
        args=args,
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
    password: str | None = None,
    message_limit: int | None = None,
    timeout: int | None = None,
) -> str:
    """status|set|cache_clear|auth|send_code"""
    return await handle_config(
        get_backend(),
        action,
        code=code,
        password=password,
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
