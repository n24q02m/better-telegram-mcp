"""Formatting utilities for text and messages."""

import json
import re
from typing import Any


def ok(data: Any) -> str:
    """Format success response as JSON string."""
    return json.dumps(data, ensure_ascii=False, default=str)


def err(message: str) -> str:
    """Format error response as JSON string."""
    return json.dumps({"error": message}, ensure_ascii=False)


def safe_error(e: Exception) -> str:
    """Return sanitized error without leaking internal details."""
    from ..backends.base import ModeError
    from ..backends.security import SecurityError

    if isinstance(e, (ModeError, SecurityError, ValueError, FileNotFoundError)):
        return err(str(e))
    return err(f"{type(e).__name__}: Operation failed. Check server logs for details.")


# ---------------------------------------------------------------------------
# Text Formatting
# ---------------------------------------------------------------------------


def escape_html(text: str) -> str:
    """
    Escape HTML special characters for Telegram.
    See: https://core.telegram.org/bots/api#html-style
    """
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def escape_markdown_v2(text: str) -> str:
    """
    Escape MarkdownV2 special characters for Telegram.
    See: https://core.telegram.org/bots/api#markdownv2-style
    """
    # Characters that MUST be escaped in MarkdownV2:
    # _ * [ ] ( ) ~ ` > # + - = | { } . !
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)


def format_bold(text: str, mode: str = "HTML") -> str:
    """Format text as bold."""
    if mode.upper() == "HTML":
        return f"<b>{escape_html(text)}</b>"
    return f"*{escape_markdown_v2(text)}*"


def format_italic(text: str, mode: str = "HTML") -> str:
    """Format text as italic."""
    if mode.upper() == "HTML":
        return f"<i>{escape_html(text)}</i>"
    return f"_{escape_markdown_v2(text)}_"


def format_code(text: str, mode: str = "HTML") -> str:
    """Format text as inline code."""
    if mode.upper() == "HTML":
        return f"<code>{escape_html(text)}</code>"
    return f"`{escape_markdown_v2(text)}`"
