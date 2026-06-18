"""Guard: telegram must depend on a mcp-core release that ships the storage seam."""

import tomllib
from pathlib import Path


def test_mcp_core_pin_includes_storage_seam():
    deps = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"][
        "dependencies"
    ]
    core = next(d for d in deps if d.startswith("n24q02m-mcp-core"))
    # StringSession seam (Subsystem A) lands at 1.18.0b8; the JWKS keys derived
    # from CREDENTIAL_SECRET (#484) + StringSession externalization (#495) needed
    # by the deployed CF image land at 1.18.0b10, and this floor pins it.
    assert "1.18.0b10" in core, f"expected >=1.18.0b10 floor, got: {core}"


def test_no_uv_path_source_for_mcp_core():
    raw = Path("pyproject.toml").read_text(encoding="utf-8")
    if "[tool.uv.sources]" in raw:
        block = raw.split("[tool.uv.sources]", 1)[1]
        assert "mcp-core" not in block.lower(), "must use PyPI dep, not a path source"
