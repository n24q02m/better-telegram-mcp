def fix_browser_open():
    path = "src/better_telegram_mcp/relay_setup.py"
    with open(path) as f:
        content = f.read()

    old_code = """    # Open browser automatically (non-blocking, best-effort)
    import asyncio
    import webbrowser

    asyncio.get_event_loop().run_in_executor(
        None, lambda: webbrowser.open(session.relay_url)
    )"""

    new_code = """    # Open browser automatically (non-blocking, best-effort)
    # Skip in CI to avoid hangs/failures
    import asyncio
    import os
    import webbrowser

    if not os.environ.get("GITHUB_ACTIONS"):
        asyncio.get_event_loop().run_in_executor(
            None, lambda: webbrowser.open(session.relay_url)
        )"""

    if old_code in content:
        content = content.replace(old_code, new_code)
        with open(path, "w") as f:
            f.write(content)
        print("Fixed browser open in relay_setup.py")
    else:
        # Try a slightly different version in case of formatting
        print("Could not find browser open code in relay_setup.py")


def fix_ty_warnings():
    path = "src/better_telegram_mcp/credential_state.py"
    with open(path) as f:
        content = f.read()

    # Remove redundant/incorrect ty: ignores
    content = content.replace("  # ty: ignore[invalid-argument-type]", "")
    content = content.replace("  # ty: ignore[union-attr]", "")

    with open(path, "w") as f:
        f.write(content)
    print("Removed ty: ignore warnings in credential_state.py")


if __name__ == "__main__":
    fix_browser_open()
    fix_ty_warnings()
