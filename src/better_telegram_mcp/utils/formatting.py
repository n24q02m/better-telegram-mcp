from __future__ import annotations

import json
from typing import Any


def ok(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def err(message: str) -> str:
    return json.dumps({"error": message}, ensure_ascii=False)
