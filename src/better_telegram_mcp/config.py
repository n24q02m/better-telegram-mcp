from __future__ import annotations

import functools
import os
from functools import cached_property
from pathlib import Path
from typing import Literal

from pydantic import model_validator
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

    # User mode (app-level credentials with built-in defaults, like Google Drive client_id/secret)
    api_id: int | None = 37984984
    api_hash: str | None = "2f5f4c76c4de7c07302380c788390100"
    phone: str | None = None
    session_name: str = "default"

    # Auth
    auth_url: str = "https://better-telegram-mcp.n24q02m.com"

    # Data
    data_dir: Path = Path.home() / ".better-telegram-mcp"

    # Security
    trusted_proxies: str | None = None

    # Runtime (derived)
    mode: Literal["bot", "user"] = "bot"

    @functools.cached_property
    def trusted_proxy_list(self) -> frozenset[str]:
        """⚡ Bolt: Memoize proxy parsing and convert to frozenset for O(1) lookups."""
        if not self.trusted_proxies:
            return frozenset()
        return frozenset(
            p.strip() for p in self.trusted_proxies.split(",") if p.strip()
        )

    @model_validator(mode="after")
    def _detect_mode(self) -> Settings:
        # Normalize empty strings to None (plugin.json sets env vars to "" by default)
        self.bot_token = _empty_to_none(self.bot_token)
        self.api_hash = _empty_to_none(self.api_hash)
        self.phone = _empty_to_none(self.phone)

        has_bot = self.bot_token is not None
        # User mode requires phone (api_id/api_hash have built-in defaults)
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
            API_ID and API_HASH use built-in defaults if not provided.

        Returns:
            A configured Settings instance.
        """
        # Mapping of relay config keys to Settings field names
        mapping = {
            "TELEGRAM_BOT_TOKEN": "bot_token",
            "TELEGRAM_PHONE": "phone",
            "TELEGRAM_API_ID": "api_id",
            "TELEGRAM_API_HASH": "api_hash",
            "TELEGRAM_SESSION_NAME": "session_name",
            "TELEGRAM_AUTH_URL": "auth_url",
            "TELEGRAM_DATA_DIR": "data_dir",
            "TELEGRAM_TRUSTED_PROXIES": "trusted_proxies",
        }

        kwargs: dict[str, object] = {}
        for config_key, field_name in mapping.items():
            val = _empty_to_none(config.get(config_key))
            if val is not None:
                kwargs[field_name] = val
            elif field_name in ("bot_token", "phone"):
                # bot_token and phone are primary credentials; if relay lacks them,
                # we explicitly pass None to override env vars (relay is the source of truth).
                kwargs[field_name] = None

        return cls(**kwargs)

    @property
    def session_path(self) -> Path:
        return self.data_dir / f"{self.session_name}.session"

    @cached_property
    def secret(self) -> str:
        """Resolve master encryption secret from env or disk."""
        # 1. Check explicit env vars (prioritize CREDENTIAL_SECRET)
        secret = (
            os.environ.get("CREDENTIAL_SECRET")
            or os.environ.get("MCP_DCR_SERVER_SECRET")
            or os.environ.get("DCR_SERVER_SECRET")
            or os.environ.get("MASTER_SECRET")
        )
        if secret:
            return secret

        # 2. Resolve or generate persistent secret on disk
        from .transports.credential_store import CredentialStore

        return CredentialStore._resolve_or_generate_secret(self.data_dir)
