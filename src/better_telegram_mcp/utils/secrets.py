"""Secret management utilities."""

from __future__ import annotations

import os
import stat
from pathlib import Path


def resolve_or_generate_secret(data_dir: Path) -> str:
    """Load persisted secret or generate a new one.

    Args:
        data_dir: Directory where the .secret file is stored.

    Returns:
        The 32-byte hex-encoded secret string.
    """
    secret_path = data_dir / ".secret"
    if secret_path.exists():
        return secret_path.read_text().strip()

    data_dir.mkdir(parents=True, exist_ok=True)
    secret = os.urandom(32).hex()
    secret_path.write_text(secret)
    try:
        secret_path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0o600
    except OSError:
        pass  # Windows may not support chmod
    return secret
