from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings


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
    auth_secret: str | None = None  # Shared secret for remote relay API

    # Data
    data_dir: Path = Path.home() / ".better-telegram-mcp"

    # Runtime (derived)
    mode: Literal["bot", "user"] = "bot"

    @model_validator(mode="after")
    def _detect_mode(self) -> Settings:
        has_user = self.api_id is not None and self.api_hash is not None
        has_bot = self.bot_token is not None

        if has_user:
            self.mode = "user"
        elif has_bot:
            self.mode = "bot"
        else:
            msg = (
                "No Telegram credentials found.\n"
                "Bot mode:  Set TELEGRAM_BOT_TOKEN (get from @BotFather)\n"
                "User mode: Set TELEGRAM_API_ID + TELEGRAM_API_HASH + TELEGRAM_PHONE\n"
                "           (get API credentials from my.telegram.org)"
            )
            raise ValueError(msg)
        return self

    @property
    def session_path(self) -> Path:
        return self.data_dir / f"{self.session_name}.session"
