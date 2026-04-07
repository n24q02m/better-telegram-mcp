import pytest

from better_telegram_mcp.transports.credential_store import CredentialStore


@pytest.fixture(autouse=True)
def clear_credential_store_cache():
    CredentialStore.clear_cache()
