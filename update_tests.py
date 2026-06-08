import sys

with open('tests/test_backends/test_user_backend.py', 'r') as f:
    lines = f.readlines()

# Add test_join_chat_private_plus_prefix to TestJoinChat
found_join_chat = False
for i, line in enumerate(lines):
    if 'class TestJoinChat:' in line:
        # Find test_join_plus_link
        for k in range(i + 1, len(lines)):
            if 'async def test_join_plus_link' in lines[k]:
                # Find the end of this method
                j = k + 1
                while j < len(lines) and (lines[j].startswith('    ') or lines[j].strip() == ''):
                    j += 1

                new_test = """
    async def test_join_chat_private_plus_prefix(self, tmp_path, mock_client, mock_client_class):
        from better_telegram_mcp.backends.user_backend import UserBackend

        settings = _make_settings(tmp_path)
        backend = UserBackend(settings)
        await backend.connect()

        # This URL should trigger line 321
        result = await backend.join_chat("https://t.me/joinchat/+abc123")

        assert result is True
"""
                lines.insert(j, new_test)
                found_join_chat = True
                break
        if found_join_chat:
            break

# Add test_secure_session_file_chmod_oserror to TestUserBackendLogging
found_logging = False
for i, line in enumerate(lines):
    if 'class TestUserBackendLogging:' in line:
        # Append to the end of the file (since it's the last class)
        lines.append("""
    async def test_secure_session_file_chmod_oserror(self, tmp_path, mock_logger):
        from better_telegram_mcp.backends.user_backend import UserBackend
        settings = _make_settings(tmp_path)
        session_file = (settings.data_dir / settings.session_name).with_suffix(".session")
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        session_file.write_text("test")

        backend = UserBackend(settings)

        with patch("better_telegram_mcp.backends.user_backend.os.chmod", side_effect=OSError("Access denied")):
            backend._secure_session_file()

        mock_logger.debug.assert_called()
        args, _ = mock_logger.debug.call_args
        assert "Could not set session file permissions" in args[0]
""")
        found_logging = True
        break

if found_join_chat and found_logging:
    with open('tests/test_backends/test_user_backend.py', 'w') as f:
        f.writelines(lines)
    print("Successfully updated tests")
else:
    print(f"Failed to find classes: join_chat={found_join_chat}, logging={found_logging}")
    sys.exit(1)
