from __future__ import annotations

import json

import pytest

from better_telegram_mcp.backends.base import ModeError
from better_telegram_mcp.tools.media import MediaOptions, handle_media


@pytest.mark.asyncio
async def test_send_photo(mock_backend):
    result = json.loads(
        await handle_media(
            mock_backend,
            MediaOptions(
                action="send_photo",
                chat_id=123,
                file_path_or_url="https://example.com/photo.jpg",
                caption="Nice photo",
            ),
        )
    )
    assert result["message_id"] == 3
    mock_backend.send_media.assert_awaited_once_with(
        123, "photo", "https://example.com/photo.jpg", caption="Nice photo"
    )


@pytest.mark.asyncio
async def test_send_file(mock_backend):
    result = json.loads(
        await handle_media(
            mock_backend,
            MediaOptions(
                action="send_file",
                chat_id=123,
                file_path_or_url="/tmp/doc.pdf",
            ),
        )
    )
    assert result["message_id"] == 3
    mock_backend.send_media.assert_awaited_once_with(
        123, "document", "/tmp/doc.pdf", caption=None
    )


@pytest.mark.asyncio
async def test_send_voice(mock_backend):
    result = json.loads(
        await handle_media(
            mock_backend,
            MediaOptions(
                action="send_voice",
                chat_id=123,
                file_path_or_url="/tmp/voice.ogg",
            ),
        )
    )
    assert result["message_id"] == 3
    mock_backend.send_media.assert_awaited_once_with(
        123, "voice", "/tmp/voice.ogg", caption=None
    )


@pytest.mark.asyncio
async def test_send_video(mock_backend):
    result = json.loads(
        await handle_media(
            mock_backend,
            MediaOptions(
                action="send_video",
                chat_id=123,
                file_path_or_url="/tmp/video.mp4",
            ),
        )
    )
    assert result["message_id"] == 3
    mock_backend.send_media.assert_awaited_once_with(
        123, "video", "/tmp/video.mp4", caption=None
    )


@pytest.mark.asyncio
async def test_send_photo_missing_params(mock_backend):
    result = json.loads(
        await handle_media(mock_backend, MediaOptions(action="send_photo", chat_id=123))
    )
    assert "error" in result

    result = json.loads(
        await handle_media(
            mock_backend,
            MediaOptions(
                action="send_photo",
                file_path_or_url="https://example.com/photo.jpg",
            ),
        )
    )
    assert "error" in result


@pytest.mark.asyncio
async def test_download(mock_backend):
    result = json.loads(
        await handle_media(
            mock_backend,
            MediaOptions(
                action="download",
                chat_id=123,
                message_id=10,
                output_dir="/tmp",
            ),
        )
    )
    assert result["path"] == "/tmp/file.jpg"


@pytest.mark.asyncio
async def test_download_missing_params(mock_backend):
    result = json.loads(
        await handle_media(mock_backend, MediaOptions(action="download", chat_id=123))
    )
    assert "error" in result

    result = json.loads(
        await handle_media(mock_backend, MediaOptions(action="download", message_id=10))
    )
    assert "error" in result


@pytest.mark.asyncio
async def test_unknown_action(mock_backend):
    result = json.loads(
        await handle_media(
            mock_backend,
            MediaOptions(
                action="unknown",
            ),
        )
    )
    assert "error" in result
    assert "Unknown action" in result["error"]


@pytest.mark.asyncio
async def test_mode_error(mock_backend):
    mock_backend.send_media.side_effect = ModeError("user")
    result = json.loads(
        await handle_media(
            mock_backend,
            MediaOptions(
                action="send_photo",
                chat_id=123,
                file_path_or_url="https://example.com/photo.jpg",
            ),
        )
    )
    assert "error" in result
    assert "user mode" in result["error"]


@pytest.mark.asyncio
async def test_general_exception(mock_backend):
    mock_backend.download_media.side_effect = RuntimeError("disk full")
    result = json.loads(
        await handle_media(
            mock_backend, MediaOptions(action="download", chat_id=123, message_id=10)
        )
    )
    assert "error" in result
    assert "RuntimeError" in result["error"]
