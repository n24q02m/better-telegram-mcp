from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from loguru import logger
from telethon import TelegramClient
from telethon.tl.functions.contacts import (
    AddContactRequest,
    BlockRequest,
    UnblockRequest,
)
from telethon.tl.types import Channel, Chat, InputPhoneContact, User

from ..config import Settings
from .base import TelegramBackend
from .security import (
    fetch_url_safely,
    validate_file_path,
    validate_output_dir,
)
from .telethon_utils import serialize_dialog, serialize_message, serialize_user


def _prepare_session_file(settings: Settings) -> None:
    """Prepare session directory and file with secure permissions."""
    s = settings
    s.data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

    # Pre-create session file with secure permissions to avoid TOCTOU
    # where Telethon creates it with default (insecure) permissions
    session_path = s.data_dir / s.session_name
    actual_session_path = session_path.with_suffix(".session")
    try:
        fd = os.open(str(actual_session_path), os.O_CREAT | os.O_WRONLY, 0o600)
        os.close(fd)
    except OSError as e:
        # Windows may not support this or file already exists
        logger.debug("Could not pre-create session file: {e}", e=e)


def _secure_session_file(settings: Settings) -> None:
    """Ensure existing session files are secured with 0o600 permissions."""
    s = settings
    session_file = (s.data_dir / s.session_name).with_suffix(".session")
    if session_file.exists():
        try:
            os.chmod(session_file, 0o600)
        except OSError as e:
            logger.debug("Could not set session file permissions: {e}", e=e)


class UserBackend(TelegramBackend):
    def __init__(self, settings: Settings):
        super().__init__("user")
        self._settings = settings
        self._client: TelegramClient | None = None

    @property
    def client(self) -> TelegramClient:
        """Return the Telethon client, ensuring it is connected."""
        if self._client is None:
            msg = "Not connected. Call connect() first."
            raise RuntimeError(msg)
        return self._client

    # --- Connection ---
    async def connect(self) -> None:
        s = self._settings
        # Bolt: Move blocking I/O to a background thread
        await asyncio.to_thread(_prepare_session_file, self._settings)

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
        client = self.client
        await client.send_code_request(phone)

    async def sign_in(
        self, phone: str, code: str, *, password: str | None = None
    ) -> dict[str, Any]:
        client = self.client
        try:
            await client.sign_in(phone, code)
        except Exception:
            if password:
                await client.sign_in(password=password)
            else:
                raise

        me = await client.get_me()
        # Bolt: Move blocking I/O to a background thread
        await asyncio.to_thread(_secure_session_file, self._settings)

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
        client = self.client
        msg = await client.send_message(
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
        client = self.client
        msg = await client.edit_message(
            chat_id, message_id, text, parse_mode=parse_mode
        )
        return serialize_message(msg)

    async def delete_message(self, chat_id: str | int, message_id: int) -> bool:
        client = self.client
        result = await client.delete_messages(chat_id, [message_id])
        # Telethon returns AffectedMessages; truthy if deleted
        return bool(result)

    async def forward_message(
        self, from_chat: str | int, to_chat: str | int, message_id: int
    ) -> dict[str, Any]:
        client = self.client
        msg = await client.forward_messages(to_chat, message_id, from_chat)
        # forward_messages may return a list or single message
        if isinstance(msg, list):
            msg = msg[0]
        return serialize_message(msg)

    async def pin_message(self, chat_id: str | int, message_id: int) -> bool:
        client = self.client
        await client.pin_message(chat_id, message_id)
        return True

    async def react_to_message(
        self, chat_id: str | int, message_id: int, emoji: str
    ) -> bool:
        client = self.client
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
        client = self.client
        entity = chat_id if chat_id is not None else None
        # Bolt: Avoid the get_messages() anti-pattern, which just calls
        # iter_messages(...).collect(). Using async comprehensions improves
        # memory efficiency without worsening network latency.
        return [
            serialize_message(msg)
            async for msg in client.iter_messages(entity, search=query, limit=limit)
        ]

    async def get_history(
        self,
        chat_id: str | int,
        *,
        limit: int = 20,
        offset_id: int | None = None,
    ) -> list[dict[str, Any]]:
        client = self.client
        kwargs: dict[str, Any] = {"limit": limit}
        if offset_id is not None:
            kwargs["offset_id"] = offset_id
        # Bolt: Avoid the get_messages() anti-pattern, which just calls
        # iter_messages(...).collect(). Using async comprehensions improves
        # memory efficiency without worsening network latency.
        return [
            serialize_message(m) async for m in client.iter_messages(chat_id, **kwargs)
        ]

    # --- Chats ---
    async def list_chats(self, *, limit: int = 50) -> list[dict[str, Any]]:
        client = self.client
        # Bolt: Using get_dialogs() is more efficient for simple listings as it
        # fetches all results in a single request, avoiding N+1 sequential I/O
        # overhead from async iteration over the stream.
        dialogs = await client.get_dialogs(limit=limit)
        return [serialize_dialog(d) for d in dialogs]

    async def get_chat_info(self, chat_id: str | int) -> dict[str, Any]:
        client = self.client
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
        client = self.client
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
        client = self.client
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
        client = self.client
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
        client = self.client
        # Bolt: Avoid the get_participants() anti-pattern, which just calls
        # iter_participants(...).collect(). Using async comprehensions improves
        # memory efficiency without worsening network latency.
        return [
            serialize_user(user)
            async for user in client.iter_participants(chat_id, limit=limit)
        ]

    async def promote_admin(
        self, chat_id: str | int, user_id: int, *, demote: bool = False
    ) -> bool:
        client = self.client
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
        client = self.client
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
        match action:
            case "list":
                return await self._topic_list(chat_id, kwargs.get("limit", 100))
            case "create":
                return await self._topic_create(chat_id, kwargs.get("name", "Topic"))
            case "close":
                return await self._topic_close(chat_id, kwargs["topic_id"])
            case _:
                return {"error": f"Unknown topic action: {action}"}

    async def _topic_list(self, chat_id: str | int, limit: int) -> dict[str, Any]:
        from telethon.tl.functions.channels import GetForumTopicsRequest

        entity = await self.client.get_entity(chat_id)
        result = await self.client(
            GetForumTopicsRequest(
                channel=entity,
                offset_date=None,
                offset_id=0,
                offset_topic=0,
                limit=limit,
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

    async def _topic_create(self, chat_id: str | int, name: str) -> dict[str, Any]:
        from telethon.tl.functions.channels import CreateForumTopicRequest

        result = await self.client(
            CreateForumTopicRequest(
                channel=chat_id,
                title=name,
                random_id=0,
            )
        )
        topic_id = result.updates[0].id if result.updates else None
        return {"topic_id": topic_id}

    async def _topic_close(self, chat_id: str | int, topic_id: int) -> dict[str, Any]:
        from telethon.tl.functions.channels import EditForumTopicRequest

        await self.client(
            EditForumTopicRequest(
                channel=chat_id,
                topic_id=topic_id,
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
        client = self.client
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
        msg = await client.send_file(chat_id, file_to_send, **kwargs)
        return serialize_message(msg)

    async def download_media(
        self,
        chat_id: str | int,
        message_id: int,
        *,
        output_dir: str | None = None,
    ) -> str:
        client = self.client
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
            safe_dir = validate_output_dir(output_dir)
            # Bolt: Move blocking I/O to a background thread
            await asyncio.to_thread(safe_dir.mkdir, parents=True, exist_ok=True)
            download_path = await client.download_media(msg, file=str(safe_dir))
        else:
            download_path = await client.download_media(msg)

        if download_path is None:
            msg_text = "Failed to download media."
            raise ValueError(msg_text)
        return str(download_path)

    # --- Contacts ---
    async def list_contacts(self) -> list[dict[str, Any]]:
        client = self.client
        from telethon.tl.functions.contacts import GetContactsRequest

        result = await client(GetContactsRequest(hash=0))
        users = getattr(result, "users", [])
        return [serialize_user(u) for u in users]

    async def search_contacts(self, query: str) -> list[dict[str, Any]]:
        client = self.client
        from telethon.tl.functions.contacts import SearchRequest

        result = await client(SearchRequest(q=query, limit=50))
        return [serialize_user(u) for u in result.users]

    async def add_contact(
        self, phone: str, first_name: str, *, last_name: str | None = None
    ) -> bool:
        client = self.client
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
        client = self.client
        if unblock:
            await client(UnblockRequest(id=user_id))
        else:
            await client(BlockRequest(id=user_id))
        return True
