from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from telethon import TelegramClient
from telethon.tl.functions.contacts import (
    AddContactRequest,
    BlockRequest,
    UnblockRequest,
)
from telethon.tl.types import Channel, Chat, InputPhoneContact, User

from ..config import Settings
from .base import TelegramBackend


class UserBackend(TelegramBackend):
    def __init__(self, settings: Settings):
        super().__init__("user")
        self._settings = settings
        self._client: TelegramClient | None = None

    def _ensure_client(self) -> TelegramClient:
        if self._client is None:
            msg = "Not connected. Call connect() first."
            raise RuntimeError(msg)
        return self._client

    @staticmethod
    def _serialize_message(msg: Any) -> dict[str, Any]:
        sender_id = None
        if msg.sender_id is not None:
            sender_id = msg.sender_id
        return {
            "message_id": msg.id,
            "text": msg.text or "",
            "date": str(msg.date) if msg.date else None,
            "sender_id": sender_id,
        }

    @staticmethod
    def _serialize_dialog(d: Any) -> dict[str, Any]:
        title = getattr(d, "title", None) or getattr(d, "name", None) or ""
        return {
            "id": d.id,
            "title": title,
            "unread_count": getattr(d, "unread_count", 0),
        }

    @staticmethod
    def _serialize_user(u: Any) -> dict[str, Any]:
        return {
            "id": u.id,
            "first_name": getattr(u, "first_name", None) or "",
            "last_name": getattr(u, "last_name", None) or "",
            "username": getattr(u, "username", None),
            "phone": getattr(u, "phone", None),
        }

    # --- Connection ---
    async def connect(self) -> None:
        s = self._settings
        # Telethon auto-appends .session, so pass path without extension
        session_path = s.data_dir / s.session_name
        s.data_dir.mkdir(parents=True, exist_ok=True)

        self._client = TelegramClient(
            str(session_path),
            s.api_id,
            s.api_hash,  # type: ignore[arg-type]
        )
        await self._client.connect()

        if not await self._client.is_user_authorized():
            await self._client.disconnect()
            self._client = None
            msg = "Session not authorized. Run: uvx better-telegram-mcp auth"
            raise ConnectionError(msg)

    async def disconnect(self) -> None:
        if self._client is not None:
            await self._client.disconnect()
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
            # Clear Telethon's entity cache
            self._client.session.cache.clear()

    # --- Messages ---
    async def send_message(
        self,
        chat_id: str | int,
        text: str,
        *,
        reply_to: int | None = None,
        parse_mode: str | None = None,
    ) -> dict[str, Any]:
        client = self._ensure_client()
        msg = await client.send_message(
            chat_id, text, reply_to=reply_to, parse_mode=parse_mode
        )
        return self._serialize_message(msg)

    async def edit_message(
        self,
        chat_id: str | int,
        message_id: int,
        text: str,
        *,
        parse_mode: str | None = None,
    ) -> dict[str, Any]:
        client = self._ensure_client()
        msg = await client.edit_message(
            chat_id, message_id, text, parse_mode=parse_mode
        )
        return self._serialize_message(msg)

    async def delete_message(self, chat_id: str | int, message_id: int) -> bool:
        client = self._ensure_client()
        result = await client.delete_messages(chat_id, [message_id])
        # Telethon returns AffectedMessages; truthy if deleted
        return bool(result)

    async def forward_message(
        self, from_chat: str | int, to_chat: str | int, message_id: int
    ) -> dict[str, Any]:
        client = self._ensure_client()
        msg = await client.forward_messages(to_chat, message_id, from_chat)
        # forward_messages may return a list or single message
        if isinstance(msg, list):
            msg = msg[0]
        return self._serialize_message(msg)

    async def pin_message(self, chat_id: str | int, message_id: int) -> bool:
        client = self._ensure_client()
        await client.pin_message(chat_id, message_id)
        return True

    async def react_to_message(
        self, chat_id: str | int, message_id: int, emoji: str
    ) -> bool:
        client = self._ensure_client()
        from telethon.tl.functions.messages import SendReactionRequest
        from telethon.tl.types import ReactionEmoji

        await client(
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
        client = self._ensure_client()
        entity = chat_id if chat_id is not None else None
        results: list[dict[str, Any]] = []
        async for msg in client.iter_messages(entity, search=query, limit=limit):
            results.append(self._serialize_message(msg))
        return results

    async def get_history(
        self,
        chat_id: str | int,
        *,
        limit: int = 20,
        offset_id: int | None = None,
    ) -> list[dict[str, Any]]:
        client = self._ensure_client()
        kwargs: dict[str, Any] = {"limit": limit}
        if offset_id is not None:
            kwargs["offset_id"] = offset_id
        messages = await client.get_messages(chat_id, **kwargs)
        return [self._serialize_message(m) for m in messages]

    # --- Chats ---
    async def list_chats(self, *, limit: int = 50) -> list[dict[str, Any]]:
        client = self._ensure_client()
        dialogs = await client.get_dialogs(limit=limit)
        return [self._serialize_dialog(d) for d in dialogs]

    async def get_chat_info(self, chat_id: str | int) -> dict[str, Any]:
        client = self._ensure_client()
        entity = await client.get_entity(chat_id)
        info: dict[str, Any] = {"id": entity.id}
        if isinstance(entity, (Channel, Chat)):
            info["title"] = getattr(entity, "title", "")
            info["participants_count"] = getattr(entity, "participants_count", None)
        elif isinstance(entity, User):
            info["first_name"] = getattr(entity, "first_name", "")
            info["last_name"] = getattr(entity, "last_name", "")
            info["username"] = getattr(entity, "username", None)
        return info

    async def create_chat(
        self, title: str, *, is_channel: bool = False
    ) -> dict[str, Any]:
        client = self._ensure_client()
        if is_channel:
            from telethon.tl.functions.channels import CreateChannelRequest

            result = await client(
                CreateChannelRequest(title=title, about="", megagroup=False)
            )
        else:
            from telethon.tl.functions.messages import CreateChatRequest

            result = await client(CreateChatRequest(title=title, users=[]))
        # Extract chat from Updates
        chat = result.chats[0] if result.chats else None
        if chat:
            return {"id": chat.id, "title": getattr(chat, "title", title)}
        return {"title": title}

    async def join_chat(self, link_or_hash: str) -> bool:
        client = self._ensure_client()
        from telethon.tl.functions.messages import ImportChatInviteRequest

        if "joinchat/" in link_or_hash or "+/" in link_or_hash:
            # Extract hash from invite link
            invite_hash = link_or_hash.split("/")[-1]
            if invite_hash.startswith("+"):
                invite_hash = invite_hash[1:]
            await client(ImportChatInviteRequest(invite_hash))
        else:
            # Public username/link
            await client(ImportChatInviteRequest(link_or_hash))
        return True

    async def leave_chat(self, chat_id: str | int) -> bool:
        client = self._ensure_client()
        from telethon.tl.functions.channels import LeaveChannelRequest

        entity = await client.get_entity(chat_id)
        if isinstance(entity, Channel):
            await client(LeaveChannelRequest(entity))
        else:
            from telethon.tl.functions.messages import DeleteChatUserRequest

            me = await client.get_me()
            await client(DeleteChatUserRequest(chat_id=entity.id, user_id=me.id))
        return True

    async def get_members(
        self, chat_id: str | int, *, limit: int = 50
    ) -> list[dict[str, Any]]:
        client = self._ensure_client()
        members: list[dict[str, Any]] = []
        async for user in client.iter_participants(chat_id, limit=limit):
            members.append(self._serialize_user(user))
        return members

    async def promote_admin(
        self, chat_id: str | int, user_id: int, *, demote: bool = False
    ) -> bool:
        client = self._ensure_client()
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
        await client(
            EditAdminRequest(
                channel=chat_id, user_id=user_id, admin_rights=rights, rank=""
            )
        )
        return True

    async def update_chat_settings(self, chat_id: str | int, **kwargs: Any) -> bool:
        client = self._ensure_client()
        if "title" in kwargs:
            from telethon.tl.functions.channels import EditTitleRequest

            await client(EditTitleRequest(channel=chat_id, title=kwargs["title"]))
        if "description" in kwargs:
            from telethon.tl.functions.channels import EditAboutRequest

            await client(EditAboutRequest(channel=chat_id, about=kwargs["description"]))
        return True

    async def manage_topics(
        self, chat_id: str | int, action: str, **kwargs: Any
    ) -> dict[str, Any]:
        client = self._ensure_client()
        match action:
            case "list":
                from telethon.tl.functions.channels import GetForumTopicsRequest

                entity = await client.get_entity(chat_id)
                result = await client(
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
            case "create":
                from telethon.tl.functions.channels import CreateForumTopicRequest

                result = await client(
                    CreateForumTopicRequest(
                        channel=chat_id,
                        title=kwargs.get("name", "Topic"),
                        random_id=0,
                    )
                )
                return {"topic_id": result.updates[0].id if result.updates else None}
            case "close":
                from telethon.tl.functions.channels import EditForumTopicRequest

                await client(
                    EditForumTopicRequest(
                        channel=chat_id,
                        topic_id=kwargs["topic_id"],
                        closed=True,
                    )
                )
                return {"closed": True}
            case _:
                return {"error": f"Unknown topic action: {action}"}

    # --- Media ---
    async def send_media(
        self,
        chat_id: str | int,
        media_type: str,
        file_path_or_url: str,
        *,
        caption: str | None = None,
    ) -> dict[str, Any]:
        client = self._ensure_client()
        kwargs: dict[str, Any] = {}
        if caption:
            kwargs["caption"] = caption
        if media_type == "voice":
            kwargs["voice_note"] = True
        elif media_type == "video":
            kwargs["video_note"] = False

        msg = await client.send_file(chat_id, file_path_or_url, **kwargs)
        return self._serialize_message(msg)

    async def download_media(
        self,
        chat_id: str | int,
        message_id: int,
        *,
        output_dir: str | None = None,
    ) -> str:
        client = self._ensure_client()
        messages = await client.get_messages(chat_id, ids=message_id)
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
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            download_path = await client.download_media(msg, file=output_dir)
        else:
            download_path = await client.download_media(msg)

        if download_path is None:
            msg_text = "Failed to download media."
            raise ValueError(msg_text)
        return str(download_path)

    # --- Contacts ---
    async def list_contacts(self) -> list[dict[str, Any]]:
        client = self._ensure_client()
        result = await client.get_contacts()
        # get_contacts returns a list of User objects
        if isinstance(result, list):
            return [self._serialize_user(u) for u in result]
        # If Contacts object with .users
        users = getattr(result, "users", [])
        return [self._serialize_user(u) for u in users]

    async def search_contacts(self, query: str) -> list[dict[str, Any]]:
        client = self._ensure_client()
        from telethon.tl.functions.contacts import SearchRequest

        result = await client(SearchRequest(q=query, limit=50))
        return [self._serialize_user(u) for u in result.users]

    async def add_contact(
        self, phone: str, first_name: str, *, last_name: str | None = None
    ) -> bool:
        client = self._ensure_client()
        result = await client(
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
        client = self._ensure_client()
        if unblock:
            await client(UnblockRequest(id=user_id))
        else:
            await client(BlockRequest(id=user_id))
        return True
