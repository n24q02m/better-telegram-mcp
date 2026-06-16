"""Guard: telegram must depend on a mcp-core release that ships the storage seam."""

import tomllib
from pathlib import Path


def test_mcp_core_pin_includes_storage_seam():
    deps = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"][
        "dependencies"
    ]
    core = next(d for d in deps if d.startswith("n24q02m-mcp-core"))
    # Storage backends + token/session sub-key usable at 1.18.0b5; the
    # StringSession seam (Subsystem A) lands at 1.18.0b8 and this floor pins it.
    assert "1.18.0b8" in core, f"expected >=1.18.0b8 floor, got: {core}"


def test_no_uv_path_source_for_mcp_core():
    raw = Path("pyproject.toml").read_text(encoding="utf-8")
    if "[tool.uv.sources]" in raw:
        block = raw.split("[tool.uv.sources]", 1)[1]
        assert "mcp-core" not in block.lower(), "must use PyPI dep, not a path source"
