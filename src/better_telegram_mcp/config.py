from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings


def _empty_to_none(v: str | None) -> str | None:
    """Treat empty or whitespace-only string as None (plugin.json sets env vars to '' by default)."""
    if not v or not v.strip():
        return None
    return v


class Settings(BaseSettings):
    model_config = {"env_prefix": "TELEGRAM_", "extra": "ignore"}

    # Bot mode
    bot_token: str | None = None

    # User mode (explicit credentials from https://my.telegram.org/apps)
    api_id: int | None = None
    api_hash: str | None = None
    phone: str | None = None
    session_name: str = "default"

    # Auth
    auth_url: str = "https://better-telegram-mcp.n24q02m.com"

    # Unified SSE
    sse_subscriber_queue_size: int = Field(default=100, gt=0)
    sse_heartbeat_seconds: int = Field(default=15, gt=0)
    bot_poll_timeout_seconds: int = Field(default=30, gt=0)
    bot_poll_backoff_initial_ms: int = Field(default=1000, gt=0)
    bot_poll_backoff_max_ms: int = Field(default=60000, gt=0)

    # Data
    data_dir: Path = Path.home() / ".better-telegram-mcp"

    # Security
    trusted_proxies: str | None = None

    # Runtime (derived)
    mode: Literal["bot", "user"] = "bot"

    @property
    def trusted_proxy_list(self) -> list[str]:
        if not self.trusted_proxies:
            return []
        return [p.strip() for p in self.trusted_proxies.split(",") if p.strip()]

    @model_validator(mode="after")
    def _detect_mode(self) -> Settings:
        # Normalize empty strings to None (plugin.json sets env vars to "" by default)
        self.bot_token = _empty_to_none(self.bot_token)
        self.api_hash = _empty_to_none(self.api_hash)
        self.phone = _empty_to_none(self.phone)

        has_bot = self.bot_token is not None
        # User mode requires explicit API credentials plus phone.
        has_user = (
            self.api_id is not None
            and self.api_hash is not None
            and self.phone is not None
        )

        if has_bot:
            self.mode = "bot"
        elif has_user:
            self.mode = "user"
        # No credentials: keep default mode="bot", server starts in unconfigured state
        return self

    @property
    def is_configured(self) -> bool:
        """Check if any Telegram credentials are provided."""
        return self.bot_token is not None or (
            self.api_id is not None
            and self.api_hash is not None
            and self.phone is not None
        )

    @classmethod
    def from_relay_config(cls, config: dict[str, str]) -> Settings:
        """Create Settings from relay config dict (from config file or relay setup).

        Args:
            config: Dict with keys like TELEGRAM_BOT_TOKEN, TELEGRAM_API_ID, etc.

        Returns:
            A configured Settings instance.
        """
        api_id = config.get("TELEGRAM_API_ID")
        api_hash = config.get("TELEGRAM_API_HASH")
        return cls(
            bot_token=config.get("TELEGRAM_BOT_TOKEN"),
            api_id=int(api_id) if api_id else None,
            api_hash=api_hash,
            phone=config.get("TELEGRAM_PHONE"),
        )

    @property
    def session_path(self) -> Path:
        return self.data_dir / f"{self.session_name}.session"
