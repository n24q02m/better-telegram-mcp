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
            "send_photo",
            MediaOptions(
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
            "send_file",
            MediaOptions(
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
            "send_voice",
            MediaOptions(
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
            "send_video",
            MediaOptions(
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
        await handle_media(mock_backend, "send_photo", MediaOptions(chat_id=123))
    )
    assert "error" in result
    assert "requires chat_id and file_path_or_url" in result["error"]

    result = json.loads(
        await handle_media(
            mock_backend,
            "send_photo",
            MediaOptions(
                file_path_or_url="https://example.com/photo.jpg",
            ),
        )
    )
    assert "error" in result
    assert "requires chat_id and file_path_or_url" in result["error"]


@pytest.mark.asyncio
async def test_download(mock_backend):
    result = json.loads(
        await handle_media(
            mock_backend,
            "download",
            MediaOptions(
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
        await handle_media(mock_backend, "download", MediaOptions(chat_id=123))
    )
    assert "error" in result
    assert "requires chat_id and message_id" in result["error"]

    result = json.loads(
        await handle_media(mock_backend, "download", MediaOptions(message_id=10))
    )
    assert "error" in result
    assert "requires chat_id and message_id" in result["error"]


@pytest.mark.asyncio
async def test_unknown_action(mock_backend):
    result = json.loads(await handle_media(mock_backend, "unknown", MediaOptions()))
    assert "error" in result
    assert "Unknown action 'unknown'" in result["error"]


@pytest.mark.asyncio
async def test_mode_error(mock_backend):
    mock_backend.send_media.side_effect = ModeError("user")
    result = json.loads(
        await handle_media(
            mock_backend,
            "send_photo",
            MediaOptions(
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
            mock_backend, "download", MediaOptions(chat_id=123, message_id=10)
        )
    )
    assert "error" in result
    assert "RuntimeError" in result["error"]


@pytest.mark.asyncio
async def test_unknown_action_suggestion(mock_backend):
    result = json.loads(await handle_media(mock_backend, "send_phot", MediaOptions()))
    assert "error" in result
    assert "Did you mean 'send_photo'?" in result["error"]

    result = json.loads(await handle_media(mock_backend, "downlo", MediaOptions()))
    assert "error" in result
    assert "Did you mean 'download'?" in result["error"]


@pytest.mark.asyncio
async def test_download_no_output_dir(mock_backend):
    result = json.loads(
        await handle_media(
            mock_backend,
            "download",
            MediaOptions(
                chat_id=123,
                message_id=10,
            ),
        )
    )
    assert result["path"] == "/tmp/file.jpg"
    mock_backend.download_media.assert_awaited_once_with(
        123, 10, output_dir=None
    )


@pytest.mark.asyncio
async def test_send_photo_string_chat_id(mock_backend):
    result = json.loads(
        await handle_media(
            mock_backend,
            "send_photo",
            MediaOptions(
                chat_id="@username",
                file_path_or_url="https://example.com/photo.jpg",
            ),
        )
    )
    assert result["message_id"] == 3
    mock_backend.send_media.assert_awaited_once_with(
        "@username", "photo", "https://example.com/photo.jpg", caption=None
    )
