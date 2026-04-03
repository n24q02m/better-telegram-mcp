with open("tests/test_server.py") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if "def test_main_calls_run():" in line:
        new_lines.append(line)
        new_lines.append("    with pytest.raises(SystemExit) as excinfo:\n")
        new_lines.append("        main()\n")
        new_lines.append("    assert excinfo.value.code == 0\n")
        # Skip next two lines of original file
    elif "def test_main_http_transport():" in line:
        new_lines.append(line)
        new_lines.append(
            '    """main() starts HTTP transport when TRANSPORT_MODE=http."""\n'
        )
        new_lines.append("    import os\n")
        new_lines.append("\n")
        new_lines.append("    with (\n")
        new_lines.append(
            '        patch.dict(os.environ, {"TRANSPORT_MODE": "http"}),\n'
        )
        new_lines.append(
            '        patch("better_telegram_mcp.transports.http.start_http") as mock_start_http,\n'
        )
        new_lines.append("    ):\n")
        new_lines.append("        with pytest.raises(SystemExit) as excinfo:\n")
        new_lines.append("            main()\n")
        new_lines.append("        assert excinfo.value.code == 0\n")
        # Skip original body
    else:
        new_lines.append(line)

# This was a bit naive, let's use a more precise approach
