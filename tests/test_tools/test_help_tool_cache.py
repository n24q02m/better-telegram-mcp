from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from better_telegram_mcp.tools.help_tool import _read_doc_sync, handle_help


@pytest.mark.asyncio
async def test_help_caching():
    # Clear cache before test if possible, but since it's a new process for pytest usually it's fine.
    # Actually, we can clear it explicitly.
    _read_doc_sync.cache_clear()

    with patch.object(Path, "read_text", return_value="Test Content") as mock_read:
        with patch.object(Path, "exists", return_value=True):
            # First call should call read_text
            res1 = await handle_help("messages")
            assert res1 == "Test Content"
            assert mock_read.call_count == 1

            # Second call should use cache
            res2 = await handle_help("messages")
            assert res2 == "Test Content"
            assert mock_read.call_count == 1

            # Different topic should call read_text again
            res3 = await handle_help("chats")
            assert res3 == "Test Content"
            assert mock_read.call_count == 2
