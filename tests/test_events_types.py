from __future__ import annotations

from better_telegram_mcp.events.types import build_event_envelope


def _make_update() -> dict[str, object]:
    return {
        "_": "UpdateNewMessage",
        "message": {"id": 1, "message": "hello"},
    }


def test_build_event_envelope_for_user_mode_uses_unified_identity() -> None:
    envelope = build_event_envelope(
        {
            "telegram_user_id": 100,
            "session_name": "user-session",
            "username": "alice",
            "mode": "user",
        },
        _make_update(),
    )

    assert envelope["mode"] == "user"
    assert envelope["event_type"] == "UpdateNewMessage"
    assert envelope["account"] == {
        "telegram_id": 100,
        "session_name": "user-session",
        "username": "alice",
        "mode": "user",
    }


def test_build_event_envelope_for_bot_mode_uses_unified_identity() -> None:
    envelope = build_event_envelope(
        {
            "telegram_id": 200,
            "session_name": "bot-session",
            "mode": "bot",
        },
        _make_update(),
    )

    assert envelope["mode"] == "bot"
    assert envelope["account"] == {
        "telegram_id": 200,
        "session_name": "bot-session",
        "mode": "bot",
    }


def test_build_event_envelope_event_id_includes_timestamp() -> None:
    """Same account+update at different times must produce different event_ids."""
    account = {
        "telegram_user_id": 100,
        "session_name": "user-session",
        "username": "alice",
        "mode": "user",
    }
    update = _make_update()

    first = build_event_envelope(account, update)
    second = build_event_envelope(account, update)

    assert first["event_id"] != second["event_id"]


def test_build_event_envelope_changes_event_id_for_different_unified_identity() -> None:
    update = _make_update()

    first = build_event_envelope(
        {
            "telegram_id": 100,
            "session_name": "user-session",
            "mode": "user",
        },
        update,
    )
    second = build_event_envelope(
        {
            "telegram_id": 200,
            "session_name": "user-session",
            "mode": "user",
        },
        update,
    )

    assert first["event_id"] != second["event_id"]


def test_build_event_envelope_changes_event_id_for_different_session_name() -> None:
    update = _make_update()

    first = build_event_envelope(
        {
            "telegram_id": 100,
            "session_name": "session-a",
            "mode": "user",
        },
        update,
    )
    second = build_event_envelope(
        {
            "telegram_id": 100,
            "session_name": "session-b",
            "mode": "user",
        },
        update,
    )

    assert first["event_id"] != second["event_id"]


def test_build_event_envelope_includes_top_level_update_id_for_bot_update() -> None:
    envelope = build_event_envelope(
        {
            "telegram_id": 200,
            "session_name": "bot-session",
            "mode": "bot",
        },
        {
            "_": "UpdateNewMessage",
            "update_id": 42,
            "message": {"id": 1, "message": "hello"},
        },
    )

    assert envelope["update_id"] == 42


def test_build_event_envelope_omits_update_id_for_user_update() -> None:
    envelope = build_event_envelope(
        {
            "telegram_id": 100,
            "session_name": "user-session",
            "mode": "user",
        },
        _make_update(),
    )

    assert "update_id" not in envelope


def test_build_event_envelope_excludes_sensitive_fields_and_replay_metadata() -> None:
    envelope = build_event_envelope(
        {
            "telegram_id": 100,
            "session_name": "user-session",
            "mode": "user",
            "phone": "+1234567890",
            "bearer_token": "secret",
        },
        _make_update(),
    )

    assert "phone" not in envelope["account"]
    assert "bearer_token" not in envelope["account"]
    assert "last_event_id" not in envelope
    assert "replay" not in envelope
