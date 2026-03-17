from __future__ import annotations

from ..backends.base import ModeError, TelegramBackend
from ..utils.formatting import err, ok, safe_error

_ACTION_TO_MEDIA_TYPE = {
    "send_photo": "photo",
    "send_file": "document",
    "send_voice": "voice",
    "send_video": "video",
}


async def handle_media(
    backend: TelegramBackend,
    action: str,
    *,
    chat_id: str | int | None = None,
    file_path_or_url: str | None = None,
    message_id: int | None = None,
    caption: str | None = None,
    output_dir: str | None = None,
) -> str:
    try:
        if action in _ACTION_TO_MEDIA_TYPE:
            if not chat_id or not file_path_or_url:
                return err(f"'{action}' requires chat_id and file_path_or_url")
            media_type = _ACTION_TO_MEDIA_TYPE[action]
            result = await backend.send_media(
                chat_id, media_type, file_path_or_url, caption=caption
            )
            return ok(result)

        if action == "download":
            if not chat_id or message_id is None:
                return err("'download' requires chat_id and message_id")
            path = await backend.download_media(
                chat_id, message_id, output_dir=output_dir
            )
            return ok({"path": path})

        return err(
            f"Unknown action '{action}'. "
            "Valid: send_photo|send_file|send_voice|send_video|download"
        )
    except ModeError as e:
        return err(str(e))
    except Exception as e:
        return safe_error(e)
