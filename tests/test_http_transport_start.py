from unittest.mock import MagicMock, patch

from better_telegram_mcp.config import Settings
from better_telegram_mcp.transports.http import start_http


def test_start_http_creates_loop_on_runtime_error():
    """Test that start_http creates a new event loop if get_event_loop raises RuntimeError."""
    mock_settings = MagicMock(spec=Settings)

    with (
        patch(
            "asyncio.get_event_loop", side_effect=RuntimeError("no running event loop")
        ),
        patch("asyncio.new_event_loop") as mock_new_loop,
        patch("asyncio.set_event_loop") as mock_set_loop,
        patch(
            "better_telegram_mcp.transports.http._is_multi_user_mode",
            return_value=False,
        ),
        patch(
            "better_telegram_mcp.transports.http._start_single_user_http"
        ) as mock_start_single,
    ):
        start_http(mock_settings)

        mock_new_loop.assert_called_once()
        mock_set_loop.assert_called_once()
        mock_start_single.assert_called_once_with(mock_settings)


def test_start_http_uses_existing_loop():
    """Test that start_http uses existing event loop if available."""
    mock_settings = MagicMock(spec=Settings)
    mock_loop = MagicMock()

    with (
        patch("asyncio.get_event_loop", return_value=mock_loop),
        patch("asyncio.new_event_loop") as mock_new_loop,
        patch(
            "better_telegram_mcp.transports.http._is_multi_user_mode", return_value=True
        ),
        patch(
            "better_telegram_mcp.transports.http._start_multi_user_http"
        ) as mock_start_multi,
    ):
        start_http(mock_settings)

        mock_new_loop.assert_not_called()
        mock_start_multi.assert_called_once_with(mock_settings)
