from __future__ import annotations

from pydantic import BaseModel, Field

from ..backends.base import ModeError, TelegramBackend
from ..utils.formatting import err, ok, safe_error

_ACTION_TO_MEDIA_TYPE = {
    "send_photo": "photo",
    "send_file": "document",
    "send_voice": "voice",
    "send_video": "video",
}


class MediaArgs(BaseModel):
    action: str = Field(
        description="send_photo|send_file|send_voice|send_video|download"
    )
    chat_id: str | int | None = None
    file_path_or_url: str | None = None
    message_id: int | None = None
    caption: str | None = None
    output_dir: str | None = None


async def handle_media(
    backend: TelegramBackend,
    args: MediaArgs,
) -> str:
    try:
        if args.action in _ACTION_TO_MEDIA_TYPE:
            if not args.chat_id or not args.file_path_or_url:
                return err(f"'{args.action}' requires chat_id and file_path_or_url")
            media_type = _ACTION_TO_MEDIA_TYPE[args.action]
            result = await backend.send_media(
                args.chat_id, media_type, args.file_path_or_url, caption=args.caption
            )
            return ok(result)

        if args.action == "download":
            if not args.chat_id or args.message_id is None:
                return err("'download' requires chat_id and message_id")
            path = await backend.download_media(
                args.chat_id, args.message_id, output_dir=args.output_dir
            )
            return ok({"path": path})

        return err(
            f"Unknown action '{args.action}'. "
            "Valid: send_photo|send_file|send_voice|send_video|download"
        )
    except ModeError as e:
        return err(str(e))
    except Exception as e:
        return safe_error(e)
