from pathlib import Path

import pytest

from better_telegram_mcp.auth.telegram_auth_provider import TelegramAuthProvider


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "data"
    d.mkdir()
    return d


@pytest.fixture
def provider(data_dir: Path) -> TelegramAuthProvider:
    return TelegramAuthProvider(data_dir, api_id=12345, api_hash="test_hash")


def test_session_owners_reverse_mapping_sync(provider: TelegramAuthProvider):
    """Verify that _bearer_to_sessions is correctly synchronized with session_owners."""
    bearer1 = "bearer1"
    bearer2 = "bearer2"

    # 1. Addition
    provider.session_owners["sid1"] = bearer1
    provider.session_owners["sid2"] = bearer1
    provider.session_owners["sid3"] = bearer2

    assert provider._bearer_to_sessions[bearer1] == {"sid1", "sid2"}
    assert provider._bearer_to_sessions[bearer2] == {"sid3"}

    # 2. Update (change bearer for a session)
    provider.session_owners["sid1"] = bearer2
    assert "sid1" not in provider._bearer_to_sessions[bearer1]
    assert provider._bearer_to_sessions[bearer1] == {"sid2"}
    assert provider._bearer_to_sessions[bearer2] == {"sid3", "sid1"}

    # 3. Deletion
    del provider.session_owners["sid2"]
    assert bearer1 not in provider._bearer_to_sessions
    assert provider._bearer_to_sessions[bearer2] == {"sid3", "sid1"}

    # 4. Pop
    val = provider.session_owners.pop("sid3")
    assert val == bearer2
    assert provider._bearer_to_sessions[bearer2] == {"sid1"}

    # 5. Clear
    provider.session_owners.clear()
    assert len(provider.session_owners) == 0
    assert len(provider._bearer_to_sessions) == 0


def test_session_owners_update_sync(provider: TelegramAuthProvider):
    """Verify that update() correctly synchronizes reverse mapping."""
    bearer1 = "bearer1"
    provider.session_owners.update({"sid1": bearer1, "sid2": bearer1})
    assert provider._bearer_to_sessions[bearer1] == {"sid1", "sid2"}

    provider.session_owners.update(sid3="bearer2")
    assert provider._bearer_to_sessions["bearer2"] == {"sid3"}
