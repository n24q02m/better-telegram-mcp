from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings


def _empty_to_none(v: str | None) -> str | None:
    """Treat empty string as None (plugin.json sets env vars to '' by default)."""
    return v if v else None


class Settings(BaseSettings):
    model_config = {"env_prefix": "TELEGRAM_", "extra": "ignore"}

    # Bot mode
    bot_token: str | None = None

    # User mode
    api_id: int | None = None
    api_hash: str | None = None
    phone: str | None = None
    session_name: str = "default"

    # Auth
    auth_url: str = "https://better-telegram-mcp.n24q02m.com"

    # Data
    data_dir: Path = Path.home() / ".better-telegram-mcp"

    # Runtime (derived)
    mode: Literal["bot", "user"] = "bot"

    @model_validator(mode="after")
    def _detect_mode(self) -> Settings:
        # Normalize empty strings to None (plugin.json sets env vars to "" by default)
        self.bot_token = _empty_to_none(self.bot_token)
        self.api_hash = _empty_to_none(self.api_hash)
        self.phone = _empty_to_none(self.phone)

        has_user = self.api_id is not None and self.api_hash is not None
        has_bot = self.bot_token is not None

        if has_user:
            self.mode = "user"
        elif has_bot:
            self.mode = "bot"
        # No credentials: keep default mode="bot", server starts in unconfigured state
        return self

    @property
    def is_configured(self) -> bool:
        """Check if any Telegram credentials are provided."""
        return self.bot_token is not None or (
            self.api_id is not None and self.api_hash is not None
        )

    @property
    def session_path(self) -> Path:
        return self.data_dir / f"{self.session_name}.session"
