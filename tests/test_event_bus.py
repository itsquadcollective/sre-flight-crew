"""Infra tests: shared event bus (DevOps cell)."""
from shared.event_bus import (
    EventBus,
    TOPIC_ERROR_DETECTED,
    TOPIC_ERROR_DIAGNOSED,
)


def test_publish_reaches_subscriber():
    bus = EventBus()
    received = []
    bus.subscribe(TOPIC_ERROR_DETECTED, received.append)
    bus.publish(TOPIC_ERROR_DETECTED, {"event_id": "e1"})
    assert received == [{"event_id": "e1"}]


def test_topics_are_isolated():
    bus = EventBus()
    received = []
    bus.subscribe(TOPIC_ERROR_DETECTED, received.append)
    bus.publish(TOPIC_ERROR_DIAGNOSED, "should not arrive")
    assert received == []


def test_bad_handler_does_not_break_others():
    bus = EventBus()
    received = []

    def bad(_):
        raise RuntimeError("boom")

    bus.subscribe(TOPIC_ERROR_DETECTED, bad)
    bus.subscribe(TOPIC_ERROR_DETECTED, received.append)
    bus.publish(TOPIC_ERROR_DETECTED, "payload")
    assert received == ["payload"]


def test_unsubscribe():
    bus = EventBus()
    received = []
    bus.subscribe(TOPIC_ERROR_DETECTED, received.append)
    bus.unsubscribe(TOPIC_ERROR_DETECTED, received.append)
    bus.publish(TOPIC_ERROR_DETECTED, "payload")
    assert received == []
