from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any


def _account_mode(account: dict[str, Any]) -> str:
    mode = account.get("mode", "user")
    return str(mode)


def _account_telegram_id(account: dict[str, Any]) -> int:
    telegram_id = account.get("telegram_id", account.get("telegram_user_id"))
    if telegram_id is None:
        msg = "account.telegram_id is required"
        raise KeyError(msg)
    return int(telegram_id)


def _normalized_account(account: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "telegram_id": _account_telegram_id(account),
        "session_name": account["session_name"],
        "mode": _account_mode(account),
    }
    if account.get("username"):
        normalized["username"] = account["username"]
    return normalized


def _canonical_event_source(
    account: dict[str, Any], update: dict[str, Any]
) -> dict[str, Any]:
    return {
        "account": _normalized_account(account),
        "update": update,
    }


def _event_id(account: dict[str, Any], update: dict[str, Any]) -> str:
    payload = json.dumps(
        _canonical_event_source(account, update),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_event_envelope(
    account: dict[str, Any], update: dict[str, Any]
) -> dict[str, Any]:
    account_payload = _normalized_account(account)

    envelope: dict[str, Any] = {
        "event_id": _event_id(account, update),
        "event_type": update.get("_", "UnknownUpdate"),
        "occurred_at": datetime.now(UTC).isoformat(),
        "mode": account_payload["mode"],
        "account": account_payload,
        "update": update,
    }
    raw_update_id = update.get("update_id")
    if raw_update_id is not None:
        envelope["update_id"] = int(raw_update_id)
    return envelope
