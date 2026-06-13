"""Tests for Telethon utility functions."""

from unittest.mock import MagicMock

from better_telegram_mcp.backends.telethon_utils import (
    serialize_dialog,
    serialize_message,
    serialize_user,
)


def test_serialize_message():
    msg = MagicMock()
    msg.id = 123
    msg.text = "Hello"
    msg.date = "2023-01-01"
    msg.sender_id = 456

    res = serialize_message(msg)
    assert res == {
        "message_id": 123,
        "text": "Hello",
        "date": "2023-01-01",
        "sender_id": 456,
    }


def test_serialize_message_none_text():
    msg = MagicMock()
    msg.id = 123
    msg.text = None
    msg.date = None
    msg.sender_id = None

    res = serialize_message(msg)
    assert res["text"] == ""
    assert res["date"] is None
    assert res["sender_id"] is None


def test_serialize_dialog():
    d = MagicMock()
    d.id = 789
    d.title = "Chat Title"
    d.unread_count = 5

    res = serialize_dialog(d)
    assert res == {
        "id": 789,
        "title": "Chat Title",
        "unread_count": 5,
    }


def test_serialize_dialog_no_title():
    d = MagicMock()
    d.id = 789
    d.title = None
    d.name = "Fallback Name"
    d.unread_count = 0

    res = serialize_dialog(d)
    assert res["title"] == "Fallback Name"


def test_serialize_user():
    u = MagicMock()
    u.id = 321
    u.first_name = "John"
    u.last_name = "Doe"
    u.username = "johndoe"
    u.phone = "123456789"

    res = serialize_user(u)
    assert res == {
        "id": 321,
        "first_name": "John",
        "last_name": "Doe",
        "username": "johndoe",
        "phone": "123456789",
    }


def test_serialize_user_minimal():
    u = MagicMock()
    u.id = 321
    u.first_name = None
    u.last_name = None
    u.username = None
    u.phone = None

    res = serialize_user(u)
    assert res["first_name"] == ""
    assert res["last_name"] == ""
    assert res["username"] is None
