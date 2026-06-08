from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from loguru import logger
from telethon import TelegramClient
from telethon.tl.functions.contacts import (
    AddContactRequest,
    BlockRequest,
    UnblockRequest,
)
from telethon.tl.types import Channel, InputPhoneContact

from ..config import Settings
from .base import TelegramBackend
from .security import (
    fetch_url_safely,
    validate_file_path,
    validate_output_dir,
)
from .user_helpers import (
    prepare_session_file,
    secure_session_file,
    serialize_dialog,
    serialize_entity,
    serialize_message,
    serialize_user,
)


class UserBackend(TelegramBackend):
    """Telegram backend using Telethon for user (MTProto) API."""

    def __init__(self, settings: Settings):
        super().__init__("user")
        self._settings = settings
        self._client: TelegramClient | None = None

    @property
    def client(self) -> TelegramClient:
        """Get the Telethon client, ensuring it is initialized."""
        if self._client is None:
            msg = "Not connected. Call connect() first."
            raise RuntimeError(msg)
        return self._client

    # --- Connection ---
    async def connect(self) -> None:
        s = self._settings
        # Bolt: Move blocking I/O to a background thread
        await asyncio.to_thread(prepare_session_file, s)

        # Telethon auto-appends .session, so pass path without extension
        session_path = s.data_dir / s.session_name
        self._client = TelegramClient(
            str(session_path),
            s.api_id,
            s.api_hash,
        )
        await self._client.connect()

        if not await self._client.is_user_authorized():
            logger.warning("Session not authorized. Auth required via config tool.")

    async def disconnect(self) -> None:
        if self._client is not None:
            try:
                await self._client.disconnect()
            except Exception as e:
                logger.warning("Error during disconnect: {e}", e=e)
            self._client = None

    async def is_connected(self) -> bool:
        if self._client is None:
            return False
        # Telethon's is_connected() is a sync method
        connected = self._client.is_connected()
        if asyncio.iscoroutine(connected):
            return await connected
        return bool(connected)

    async def clear_cache(self) -> None:
        if self._client is not None and self._client.session:
            # Clear Telethon's entity cache by deleting cached entities
            try:
                self._client.session.save()
            except Exception as e:
                logger.warning("Error saving session during clear_cache: {e}", e=e)

    # --- Auth ---
    async def is_authorized(self) -> bool:
        if self._client is None:
            return False
        return await self._client.is_user_authorized()

    async def send_code(self, phone: str) -> None:
        await self.client.send_code_request(phone)

    async def sign_in(
        self, phone: str, code: str, *, password: str | None = None
    ) -> dict[str, Any]:
        try:
            await self.client.sign_in(phone, code)
        except Exception:
            if password:
                await self.client.sign_in(password=password)
            else:
                raise

        me = await self.client.get_me()
        # Bolt: Move blocking I/O to a background thread
        await asyncio.to_thread(secure_session_file, self._settings)

        return {
            "authenticated_as": getattr(me, "first_name", ""),
            "username": getattr(me, "username", None),
        }

    # --- Messages ---
    async def send_message(
        self,
        chat_id: str | int,
        text: str,
        *,
        reply_to: int | None = None,
        parse_mode: str | None = None,
    ) -> dict[str, Any]:
        msg = await self.client.send_message(
            chat_id, text, reply_to=reply_to, parse_mode=parse_mode
        )
        return serialize_message(msg)

    async def edit_message(
        self,
        chat_id: str | int,
        message_id: int,
        text: str,
        *,
        parse_mode: str | None = None,
    ) -> dict[str, Any]:
        msg = await self.client.edit_message(
            chat_id, message_id, text, parse_mode=parse_mode
        )
        return serialize_message(msg)

    async def delete_message(self, chat_id: str | int, message_id: int) -> bool:
        result = await self.client.delete_messages(chat_id, [message_id])
        return bool(result and result[0].pts) if result else False

    async def forward_message(
        self, from_chat: str | int, to_chat: str | int, message_id: int
    ) -> dict[str, Any]:
        msgs = await self.client.forward_messages(to_chat, message_id, from_chat)
        # forward_messages returns a list even for single ID
        msg = msgs[0] if msgs else None
        return serialize_message(msg) if msg else {}

    async def pin_message(self, chat_id: str | int, message_id: int) -> bool:
        result = await self.client.pin_message(chat_id, message_id)
        return bool(result)

    async def react_to_message(
        self, chat_id: str | int, message_id: int, emoji: str
    ) -> bool:
        from telethon.tl.functions.messages import SendReactionRequest
        from telethon.tl.types import ReactionEmoji

        await self.client(
            SendReactionRequest(
                peer=chat_id,
                msg_id=message_id,
                reaction=[ReactionEmoji(emoticon=emoji)],
            )
        )
        return True

    async def search_messages(
        self,
        query: str,
        *,
        chat_id: str | int | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        # Bolt: Avoid materializing lists with .collect()
        return [
            serialize_message(m)
            async for m in self.client.iter_messages(chat_id, search=query, limit=limit)
        ]

    async def get_history(
        self,
        chat_id: str | int,
        *,
        limit: int = 20,
        offset_id: int | None = None,
    ) -> list[dict[str, Any]]:
        # Bolt: Avoid materializing lists with .collect()
        return [
            serialize_message(m)
            async for m in self.client.iter_messages(
                chat_id, limit=limit, offset_id=offset_id or 0
            )
        ]

    # --- Chats ---
    async def list_chats(self, *, limit: int = 50) -> list[dict[str, Any]]:
        # Bolt: get_dialogs(limit=...) fetches in one request, no N+1 I/O issue.
        dialogs = await self.client.get_dialogs(limit=limit)
        return [serialize_dialog(d) for d in dialogs]

    async def get_chat_info(self, chat_id: str | int) -> dict[str, Any]:
        entity = await self.client.get_entity(chat_id)
        return serialize_entity(entity)

    async def create_chat(
        self, title: str, *, is_channel: bool = False
    ) -> dict[str, Any]:
        if is_channel:
            from telethon.tl.functions.channels import CreateChannelRequest

            result = await self.client(
                CreateChannelRequest(title=title, about="", megagroup=False)
            )
        else:
            from telethon.tl.functions.messages import CreateChatRequest

            result = await self.client(CreateChatRequest(title=title, users=[]))
        # Extract chat from Updates
        chat = result.chats[0] if result.chats else None
        if chat:
            return {"id": chat.id, "title": getattr(chat, "title", title)}
        return {"title": title}

    async def join_chat(self, link_or_hash: str) -> bool:
        from telethon.tl.functions.messages import ImportChatInviteRequest

        if "joinchat/" in link_or_hash or "+/" in link_or_hash:
            # Extract hash from invite link
            invite_hash = link_or_hash.split("/")[-1]
            if invite_hash.startswith("+"):
                invite_hash = invite_hash[1:]
            await self.client(ImportChatInviteRequest(invite_hash))
        else:
            # Public username/link
            await self.client(ImportChatInviteRequest(link_or_hash))
        return True

    async def leave_chat(self, chat_id: str | int) -> bool:
        from telethon.tl.functions.channels import LeaveChannelRequest

        entity = await self.client.get_entity(chat_id)
        if isinstance(entity, Channel):
            await self.client(LeaveChannelRequest(entity))
        else:
            from telethon.tl.functions.messages import DeleteChatUserRequest

            me = await self.client.get_me()
            await self.client(DeleteChatUserRequest(chat_id=entity.id, user_id=me.id))
        return True

    async def get_members(
        self, chat_id: str | int, *, limit: int = 50
    ) -> list[dict[str, Any]]:
        # Bolt: Avoid the get_participants() anti-pattern, which just calls
        # iter_participants(...).collect(). Using async comprehensions improves
        # memory efficiency without worsening network latency.
        return [
            serialize_user(user)
            async for user in self.client.iter_participants(chat_id, limit=limit)
        ]

    async def promote_admin(
        self, chat_id: str | int, user_id: int, *, demote: bool = False
    ) -> bool:
        from telethon.tl.functions.channels import EditAdminRequest
        from telethon.tl.types import ChatAdminRights

        if demote:
            rights = ChatAdminRights()
        else:
            rights = ChatAdminRights(
                post_messages=True,
                edit_messages=True,
                delete_messages=True,
                ban_users=True,
                invite_users=True,
                pin_messages=True,
                manage_call=True,
            )
        await self.client(
            EditAdminRequest(
                channel=chat_id, user_id=user_id, admin_rights=rights, rank=""
            )
        )
        return True

    async def update_chat_settings(self, chat_id: str | int, **kwargs: Any) -> bool:
        if "title" in kwargs:
            from telethon.tl.functions.channels import EditTitleRequest

            await self.client(EditTitleRequest(channel=chat_id, title=kwargs["title"]))
        if "description" in kwargs:
            from telethon.tl.functions.channels import EditAboutRequest

            await self.client(
                EditAboutRequest(channel=chat_id, about=kwargs["description"])
            )
        return True

    async def manage_topics(
        self, chat_id: str | int, action: str, **kwargs: Any
    ) -> dict[str, Any]:
        match action:
            case "list":
                return await self._list_topics(chat_id, **kwargs)
            case "create":
                return await self._create_topic(chat_id, **kwargs)
            case "close":
                return await self._close_topic(chat_id, **kwargs)
            case _:
                return {"error": f"Unknown topic action: {action}"}

    async def _list_topics(self, chat_id: str | int, **kwargs: Any) -> dict[str, Any]:
        from telethon.tl.functions.channels import GetForumTopicsRequest

        entity = await self.client.get_entity(chat_id)
        result = await self.client(
            GetForumTopicsRequest(
                channel=entity,
                offset_date=None,
                offset_id=0,
                offset_topic=0,
                limit=kwargs.get("limit", 100),
            )
        )
        topics = [
            {
                "id": t.id,
                "title": t.title,
                "icon_emoji_id": getattr(t, "icon_emoji_id", None),
            }
            for t in result.topics
        ]
        return {"topics": topics, "count": len(topics)}

    async def _create_topic(self, chat_id: str | int, **kwargs: Any) -> dict[str, Any]:
        from telethon.tl.functions.channels import CreateForumTopicRequest

        result = await self.client(
            CreateForumTopicRequest(
                channel=chat_id,
                title=kwargs.get("name", "Topic"),
                random_id=0,
            )
        )
        return {"topic_id": result.updates[0].id if result.updates else None}

    async def _close_topic(self, chat_id: str | int, **kwargs: Any) -> dict[str, Any]:
        from telethon.tl.functions.channels import EditForumTopicRequest

        await self.client(
            EditForumTopicRequest(
                channel=chat_id,
                topic_id=kwargs["topic_id"],
                closed=True,
            )
        )
        return {"closed": True}

    # --- Media ---
    async def send_media(
        self,
        chat_id: str | int,
        media_type: str,
        file_path_or_url: str,
        *,
        caption: str | None = None,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        if caption:
            kwargs["caption"] = caption
        if media_type == "voice":
            kwargs["voice_note"] = True
        elif media_type == "video":
            kwargs["video_note"] = False

        if file_path_or_url.strip().lower().startswith(("http://", "https://")):
            file_to_send = await fetch_url_safely(file_path_or_url.strip())
        else:
            file_to_send = validate_file_path(file_path_or_url)
        msg = await self.client.send_file(chat_id, file_to_send, **kwargs)
        return serialize_message(msg)

    async def download_media(
        self,
        chat_id: str | int,
        message_id: int,
        *,
        output_dir: str | None = None,
    ) -> str:
        messages = await self.client.get_messages(chat_id, ids=message_id)
        msg = (
            messages
            if not isinstance(messages, list)
            else messages[0]
            if messages
            else None
        )
        if msg is None or msg.media is None:
            msg_text = "Message has no media to download."
            raise ValueError(msg_text)

        download_path: Path | str | None = None
        if output_dir:
            safe_dir = validate_output_dir(output_dir)
            # Bolt: Move blocking I/O to a background thread
            await asyncio.to_thread(safe_dir.mkdir, parents=True, exist_ok=True)
            download_path = await self.client.download_media(msg, file=str(safe_dir))
        else:
            download_path = await self.client.download_media(msg)

        if download_path is None:
            msg_text = "Failed to download media."
            raise ValueError(msg_text)
        return str(download_path)

    # --- Contacts ---
    async def list_contacts(self) -> list[dict[str, Any]]:
        from telethon.tl.functions.contacts import GetContactsRequest

        result = await self.client(GetContactsRequest(hash=0))
        users = getattr(result, "users", [])
        return [serialize_user(u) for u in users]

    async def search_contacts(self, query: str) -> list[dict[str, Any]]:
        from telethon.tl.functions.contacts import SearchRequest

        result = await self.client(SearchRequest(q=query, limit=50))
        return [serialize_user(u) for u in result.users]

    async def add_contact(
        self, phone: str, first_name: str, *, last_name: str | None = None
    ) -> bool:
        result = await self.client(
            AddContactRequest(
                id=InputPhoneContact(
                    client_id=0,
                    phone=phone,
                    first_name=first_name,
                    last_name=last_name or "",
                ),
                first_name=first_name,
                last_name=last_name or "",
                phone=phone,
            )
        )
        return bool(result)

    async def block_user(self, user_id: int, *, unblock: bool = False) -> bool:
        if unblock:
            await self.client(UnblockRequest(id=user_id))
        else:
            await self.client(BlockRequest(id=user_id))
        return True
