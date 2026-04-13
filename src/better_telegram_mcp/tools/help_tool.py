from __future__ import annotations

import asyncio
from pathlib import Path

from ..utils.formatting import err

_DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"

_VALID_TOPICS = {"messages", "chats", "media", "contacts"}


async def handle_help(topic: str | None = None) -> str:
    if topic is None or topic in ("all", "telegram"):
        # Bolt: Load all documentation files concurrently to reduce I/O wait time
        tasks = [_load_doc(t) for t in sorted(_VALID_TOPICS)]
        results = await asyncio.gather(*tasks)
        parts = [doc for doc in results if doc]
        if parts:
            return "\n\n---\n\n".join(parts)
        return err("No documentation found.")

    if topic not in _VALID_TOPICS:
        import difflib

        closest = difflib.get_close_matches(
            topic, [*_VALID_TOPICS, "all", "telegram"], n=1
        )
        suggestion = f" Did you mean '{closest[0]}'?" if closest else ""
        return err(
            f"Unknown topic '{topic}'.{suggestion} "
            "Valid: telegram|messages|chats|media|contacts|all"
        )

    doc = await _load_doc(topic)
    if doc:
        return doc
    return err(f"Documentation for '{topic}' not found.")


async def _load_doc(topic: str) -> str | None:
    path = _DOCS_DIR / f"{topic}.md"
    if path.exists():
        # Bolt: Read file asynchronously to prevent blocking the event loop
        content = await asyncio.to_thread(path.read_text, encoding="utf-8")
        return content.strip()
    return None
