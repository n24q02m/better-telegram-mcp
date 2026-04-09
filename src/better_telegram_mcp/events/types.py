from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any


def _canonical_event_source(
    account: dict[str, Any], update: dict[str, Any]
) -> dict[str, Any]:
    return {
        "account": {"telegram_user_id": account["telegram_user_id"]},
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
    account_payload = {
        "telegram_user_id": account["telegram_user_id"],
        "session_name": account["session_name"],
    }
    if account.get("username"):
        account_payload["username"] = account["username"]

    return {
        "event_id": _event_id(account, update),
        "event_type": update.get("_", "UnknownUpdate"),
        "occurred_at": datetime.now(UTC).isoformat(),
        "account": account_payload,
        "update": update,
    }
