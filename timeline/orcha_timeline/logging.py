from __future__ import annotations

import json
import typing
from dataclasses import dataclass, field
from enum import Enum
from time import time

import logging
import logging.handlers as handlers

if typing.TYPE_CHECKING:
    from typing import Any, Optional


LOG_FILE = "/var/log/orcha-timeline"

_logger = None


class EventType(str, Enum):
    Start = "start"
    End = "end"
    Instant = "instant"


@dataclass
class Event:
    type: EventType
    name: str
    id: Optional[str] = None
    track: Optional[str] = None
    render_data: dict[str, Any] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time)

    def serialize(self):
        return json.dumps(
            {
                "type": self.type,
                "ts": self.ts,
                "name": self.name,
                "id": self.id,
                "track": self.track,
                "render_data": self.render_data,
                "data": self.data,
            }
        )


def get_logger():
    logger = logging.getLogger("orcha-timeline")
    if not logger.hasHandlers():
        handler = handlers.TimedRotatingFileHandler(LOG_FILE, when="W6", backupCount=4)
        handler.setFormatter(logging.Formatter("%(message)s"))

        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
    return logger


def log(event: Event):
    global _logger
    if _logger is None:
        _logger = get_logger()
    _logger.info(event.serialize())
