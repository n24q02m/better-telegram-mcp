from __future__ import annotations

from better_telegram_mcp.events.sse_fanout_hub import SSEFanoutHub


def _make_event(event_id: str) -> dict[str, object]:
    return {
        "event_id": event_id,
        "event_type": "UpdateNewMessage",
        "mode": "user",
        "account": {
            "telegram_id": 100,
            "session_name": "alice",
            "mode": "user",
        },
        "update": {"_": "UpdateNewMessage", "message": {"id": 1}},
    }


async def test_publish_delivers_event_to_active_subscriber() -> None:
    hub = SSEFanoutHub(subscriber_queue_size=2)
    subscriber = hub.subscribe()

    assert hub.publish(_make_event("evt-1")) is True

    item = await subscriber.next_item()
    assert item.kind == "event"
    assert item.event == _make_event("evt-1")
    assert item.reason is None


async def test_second_subscribe_replaces_existing_connection() -> None:
    hub = SSEFanoutHub(subscriber_queue_size=2)
    first = hub.subscribe()
    second = hub.subscribe()

    replaced = await first.next_item()
    assert replaced.kind == "error"
    assert replaced.reason == "connection_replaced"

    assert hub.publish(_make_event("evt-2")) is True
    delivered = await second.next_item()
    assert delivered.kind == "event"
    assert delivered.event == _make_event("evt-2")


async def test_overflow_closes_subscriber_without_blocking_publish() -> None:
    hub = SSEFanoutHub(subscriber_queue_size=1)
    subscriber = hub.subscribe()

    assert hub.publish(_make_event("evt-1")) is True
    assert hub.publish(_make_event("evt-2")) is False

    overflow = await subscriber.next_item()
    assert overflow.kind == "error"
    assert overflow.reason == "overflow"


async def test_close_notifies_subscriber_and_stops_future_delivery() -> None:
    hub = SSEFanoutHub(subscriber_queue_size=2)
    subscriber = hub.subscribe()

    await hub.close("runtime_stopped")

    stopped = await subscriber.next_item()
    assert stopped.kind == "error"
    assert stopped.reason == "runtime_stopped"
    assert hub.publish(_make_event("evt-3")) is False


async def test_publish_without_subscriber_is_dropped() -> None:
    hub = SSEFanoutHub(subscriber_queue_size=2)

    assert hub.publish(_make_event("evt-4")) is False
