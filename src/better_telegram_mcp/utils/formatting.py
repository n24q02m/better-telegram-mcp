"""Formatting utilities for text and messages."""

import json
import re
from typing import Any


def ok(data: Any) -> str:
    """Return a successful MCP tool response."""
    return json.dumps(data, ensure_ascii=False, default=str)


def err(message: str) -> str:
    """Return an error MCP tool response."""
    return json.dumps({"error": message}, ensure_ascii=False)


def safe_error(e: Exception) -> str:
    """Return sanitized error without leaking internal details."""
    from ..backends.base import ModeError
    from ..backends.security import SecurityError

    if isinstance(e, (ModeError, SecurityError, ValueError, FileNotFoundError)):
        return err(str(e))
    return err(f"{type(e).__name__}: Operation failed. Check server logs for details.")


# --- Telegram Styling Helpers ---


def escape_html(text: str) -> str:
    """Escape text for use in HTML parse_mode."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def escape_markdown_v2(text: str, entity_type: str | None = None) -> str:
    """
    Escape text for use in MarkdownV2 parse_mode.

    Args:
        text: The text to escape.
        entity_type: Special context like 'code', 'pre', 'link_text', or 'link_url'.
    """
    if entity_type in ("code", "pre"):
        return re.sub(r"([`\\])", r"\\\1", text)
    if entity_type == "link_text":
        return re.sub(r"([\[\]\\])", r"\\\1", text)
    if entity_type == "link_url":
        return re.sub(r"([)\\])", r"\\\1", text)

    return re.sub(r"([_*\[\]()~`>#+\-=|{}.!])", r"\\\1", text)


def bold(text: str, mode: str | None = "HTML") -> str:
    """Format text as bold."""
    if mode == "MarkdownV2":
        return f"*{escape_markdown_v2(text)}*"
    return f"<b>{escape_html(text)}</b>"


def italic(text: str, mode: str | None = "HTML") -> str:
    """Format text as italic."""
    if mode == "MarkdownV2":
        return f"_{escape_markdown_v2(text)}_"
    return f"<i>{escape_html(text)}</i>"


def code(text: str, mode: str | None = "HTML") -> str:
    """Format text as inline code."""
    if mode == "MarkdownV2":
        return f"`{escape_markdown_v2(text, entity_type='code')}`"
    return f"<code>{escape_html(text)}</code>"


def pre(text: str, mode: str | None = "HTML", language: str | None = None) -> str:
    """Format text as a code block."""
    if mode == "MarkdownV2":
        lang = escape_markdown_v2(language) if language else ""
        return f"```{lang}\n{escape_markdown_v2(text, entity_type='pre')}\n```"
    lang_attr = f' class="language-{language}"' if language else ""
    return f"<pre{lang_attr}>{escape_html(text)}</pre>"


def link(text: str, url: str, mode: str | None = "HTML") -> str:
    """Format an inline link."""
    if mode == "MarkdownV2":
        e_text = escape_markdown_v2(text, entity_type="link_text")
        e_url = escape_markdown_v2(url, entity_type="link_url")
        return f"[{e_text}]({e_url})"
    return f'<a href="{escape_html(url)}">{escape_html(text)}</a>'
