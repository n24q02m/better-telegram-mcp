from __future__ import annotations

import functools
import os
from functools import cached_property
from pathlib import Path
from typing import Literal

from loguru import logger
from mcp_core.auth import BundledClientSpec, resolve_bundled_client
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings


def _empty_to_none(v: str | None) -> str | None:
    """Treat empty or whitespace-only string as None (plugin.json sets env vars to '' by default)."""
    if not v or not v.strip():
        return None
    return v


# Default data dir (Telethon ``*.session`` files, ``user_sessions/``, the
# HTTP-mode ``.secret``). Renamed with the project; the pre-rename directory
# is moved over once on first use. ``TELEGRAM_DATA_DIR`` bypasses all of this.
# Not to be confused with mcp-core's ``~/.telegram-mcp/`` (PerPluginStore
# ``"telegram"``), which mcp-core derives itself and is not moved here.
DATA_DIR_NAME = ".telegram"
LEGACY_DATA_DIR_NAME = ".better-telegram-mcp"


def _holds_server_state(directory: Path) -> bool:
    """True if ``directory`` contains files this server writes."""
    return (
        (directory / ".secret").exists()
        or (directory / "user_sessions").exists()
        or any(directory.glob("*.session"))
    )


def resolve_default_data_dir() -> Path:
    """Return the default data dir, moving the legacy one over once.

    - ``~/.telegram`` exists and holds server state (or no legacy dir
      exists): use it.
    - Only ``~/.better-telegram-mcp`` exists: rename it to ``~/.telegram``,
      read back that the move landed, and use the new path. If the rename
      fails (for example a file is still open by an old process on Windows)
      or the readback does not match, keep reading the legacy dir.
    - Both exist but ``~/.telegram`` holds none of this server's files (an
      unrelated directory): keep the legacy dir rather than strand its
      sessions.
    """
    home = Path.home()
    target = home / DATA_DIR_NAME
    legacy = home / LEGACY_DATA_DIR_NAME

    if not legacy.exists():
        return target
    if target.exists():
        if _holds_server_state(target):
            logger.warning(
                "Both {} and legacy {} exist; using {}. The legacy dir was left "
                "untouched -- remove it once nothing reads it.",
                target,
                legacy,
                target,
            )
            return target
        logger.warning(
            "{} exists but holds no telegram server state; still reading legacy "
            "{}. Set TELEGRAM_DATA_DIR to choose explicitly.",
            target,
            legacy,
        )
        return legacy

    try:
        os.rename(legacy, target)
    except OSError as exc:
        logger.warning(
            "Could not move legacy data dir {} to {} ({}); reading the legacy "
            "dir for now.",
            legacy,
            target,
            exc,
        )
        return legacy

    if target.is_dir() and not legacy.exists():
        logger.info("Moved data dir {} -> {}", legacy, target)
        return target
    logger.warning(
        "Data dir move {} -> {} did not read back as expected; reading the legacy dir.",
        legacy,
        target,
    )
    return legacy if legacy.exists() else target


# Telegram api_id/api_hash identity (BYO resolver chain: CLI (unused here) >
# env pair > bundled default, unless USE_BUNDLED_TELEGRAM_CLIENT explicitly
# disables it). This is Telegram's own public desktop app pair
# (https://core.telegram.org/api/obtaining_api_id) -- hardcoding it here is
# safe and gives users zero-config user-mode after relay submit.
_BUNDLED_TELEGRAM_API_ID = "37984984"
_BUNDLED_TELEGRAM_API_HASH = "2f5f4c76c4de7c07302380c788390100"  # gitleaks:allow
_TELEGRAM_CLIENT_SPEC = BundledClientSpec(
    provider="telegram",
    env_id="TELEGRAM_API_ID",
    env_secret="TELEGRAM_API_HASH",
    bundled_id=_BUNDLED_TELEGRAM_API_ID,
    bundled_secret=_BUNDLED_TELEGRAM_API_HASH,
    use_bundled_env="USE_BUNDLED_TELEGRAM_CLIENT",
)


class Settings(BaseSettings):
    model_config = {"env_prefix": "TELEGRAM_", "extra": "ignore"}

    # Bot mode
    bot_token: str | None = None

    # User mode (app-level credentials with built-in defaults, like Google Drive client_id/secret)
    api_id: int | None = Field(
        default_factory=lambda: int(
            resolve_bundled_client(_TELEGRAM_CLIENT_SPEC).client_id
        )
    )
    api_hash: str | None = Field(
        default_factory=lambda: (
            resolve_bundled_client(_TELEGRAM_CLIENT_SPEC).client_secret
        )
    )
    phone: str | None = None
    session_name: str = "default"

    # Data
    data_dir: Path = Field(default_factory=resolve_default_data_dir)

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

    @property
    def cf_mode(self) -> bool:
        """True when durable state is externalized to a CF backend (cf-kv)."""
        return os.environ.get("MCP_STORAGE_BACKEND", "").lower() == "cf-kv"

    @classmethod
    def from_relay_config(cls, config: dict[str, str]) -> Settings:
        """Create Settings from relay config dict (from config file or relay setup).

        Args:
            config: Dict with keys like TELEGRAM_BOT_TOKEN, TELEGRAM_API_ID, etc.
            API_ID and API_HASH use built-in defaults if not provided.

        Returns:
            A configured Settings instance.
        """
        kwargs: dict[str, object] = {
            "bot_token": config.get("TELEGRAM_BOT_TOKEN"),
            "phone": config.get("TELEGRAM_PHONE"),
        }
        # Only override defaults if relay explicitly provides values
        if config.get("TELEGRAM_API_ID"):
            kwargs["api_id"] = int(config["TELEGRAM_API_ID"])
        if config.get("TELEGRAM_API_HASH"):
            kwargs["api_hash"] = config["TELEGRAM_API_HASH"]
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
