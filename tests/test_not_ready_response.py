import better_telegram_mcp.server as srv


def test_not_ready_response_unconfigured():
    """Test _not_ready_response when _unconfigured is True."""
    old_unconfigured = srv._unconfigured
    try:
        srv._unconfigured = True
        data = srv._not_ready_response()
        assert data["error"] == "Not configured"
        assert "setup" in data
        assert "relay" in data["setup"]
    finally:
        srv._unconfigured = old_unconfigured


def test_not_ready_response_authenticated_error():
    """Test _not_ready_response when _unconfigured is False."""
    old_unconfigured = srv._unconfigured
    try:
        srv._unconfigured = False
        data = srv._not_ready_response()
        assert "error" in data
        assert "not authenticated" in data["error"].lower()
    finally:
        srv._unconfigured = old_unconfigured
