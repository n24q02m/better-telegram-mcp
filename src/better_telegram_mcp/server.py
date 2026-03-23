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

    auth_handler = None
    if _settings.mode == "user" and not await _backend.is_authorized():
        if _settings.phone:
            _pending_auth = True
            auth_handler, _auth_url = await _start_auth(_backend, _settings)
            logger.warning(
                "Session not authorized. Open {} to authenticate.", _auth_url
            )

            import webbrowser

            try:
                # Bolt: webbrowser.open() is a synchronous, blocking call that invokes an external GUI process.
                # Offloading it to a separate thread prevents blocking the async event loop, ensuring
                # the MCP server remains responsive to incoming requests during the auth flow.
                await asyncio.to_thread(webbrowser.open, _auth_url)
            except Exception:
                pass

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
    """send|edit|delete|forward|pin|react|search|history

    parse_mode options for send/edit:
    - "HTML": <b>bold</b> <i>italic</i> <code>code</code> <a href="url">link</a>
    - "MarkdownV2": *bold* _italic_ `code` [link](url) — escape special chars: \\. \\! \\( \\)
    - "Markdown": *bold* _italic_ `code` [link](url) — legacy, fewer features
    - None: plain text (default)

    chat_id formats: positive int (user), negative int (group/supergroup), @username (public chat)."""
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
    """list|info|create|join|leave|members|admin|settings|topics

    chat_id formats:
    - Positive integer: private user chat (e.g. 123456789)
    - Negative integer: group or supergroup (e.g. -1001234567890)
    - @username: public group or channel (e.g. @mychannel)

    Use 'list' to discover available chat IDs, then use them in other tools."""
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
    """send_photo|send_file|send_voice|send_video|download

    Media types and limits (Bot API):
    - send_photo: JPEG/PNG/WebP, max 10 MB (compressed), 5 MB via URL
    - send_file: any file type, max 50 MB (2 GB via local file in user mode)
    - send_voice: OGG/OPUS audio, max 50 MB
    - send_video: MP4 (H.264+AAC), max 50 MB (2 GB via local file in user mode)
    - download: saves media from a message to output_dir

    file_path_or_url accepts local file path or HTTP(S) URL."""
    if _pending_auth:
        return _auth_required_response()
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
    """list|search|add|block (user mode only)"""
    if _pending_auth:
        return _auth_required_response()

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
    """status|set|cache_clear"""
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
    """Full documentation. Topics: messages|chats|media|contacts|all"""
    return handle_help(topic)


# --- Resources ---
from .resources import register_resources  # noqa: E402

register_resources(mcp)


def main() -> None:
    mcp.run(transport="stdio")
