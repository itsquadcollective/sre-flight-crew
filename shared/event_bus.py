"""Tiny in-process pub/sub bus so the agents stay decoupled.

Usage:
    from shared.event_bus import bus
    bus.subscribe("error.detected", handler)
    bus.publish("error.detected", error_event)

Pipeline topics (payloads are the dataclasses from shared/schemas.py):
    error.detected     ErrorEvent       Watchman  -> Diagnoser
    error.diagnosed    DiagnosisResult  Diagnoser -> Fixer
    error.fixed        FixResult        Fixer     -> Dashboard / Watchman
    system.status      SystemStatus     anyone    -> Dashboard
"""
import logging
import threading
from collections import defaultdict
from typing import Any, Callable

logger = logging.getLogger(__name__)

Handler = Callable[[Any], None]

# Canonical topic names — import these instead of hardcoding strings
TOPIC_ERROR_DETECTED = "error.detected"
TOPIC_ERROR_DIAGNOSED = "error.diagnosed"
TOPIC_ERROR_FIXED = "error.fixed"
TOPIC_SYSTEM_STATUS = "system.status"


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)
        self._lock = threading.Lock()

    def subscribe(self, topic: str, handler: Handler) -> None:
        with self._lock:
            self._handlers[topic].append(handler)

    def unsubscribe(self, topic: str, handler: Handler) -> None:
        with self._lock:
            if handler in self._handlers.get(topic, []):
                self._handlers[topic].remove(handler)

    def publish(self, topic: str, payload: Any = None) -> None:
        with self._lock:
            handlers = list(self._handlers.get(topic, []))
        for handler in handlers:
            try:
                handler(payload)
            except Exception:  # one bad handler must not kill the pipeline
                logger.exception("Handler error on topic %s", topic)


# Singleton shared by the whole process
bus = EventBus()
