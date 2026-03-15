from __future__ import annotations

from pathlib import Path

from ..utils.formatting import err

_DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"

_VALID_TOPICS = {"messages", "chats", "media", "contacts"}


def handle_help(topic: str | None = None) -> str:
    if topic is None or topic == "all":
        parts: list[str] = []
        for t in sorted(_VALID_TOPICS):
            doc = _load_doc(t)
            if doc:
                parts.append(doc)
        if parts:
            return "\n\n---\n\n".join(parts)
        return err("No documentation found.")

    if topic not in _VALID_TOPICS:
        return err(f"Unknown topic '{topic}'. Valid: messages|chats|media|contacts|all")

    doc = _load_doc(topic)
    if doc:
        return doc
    return err(f"Documentation for '{topic}' not found.")


def _load_doc(topic: str) -> str | None:
    path = _DOCS_DIR / f"{topic}.md"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return None
