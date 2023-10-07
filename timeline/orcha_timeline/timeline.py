from __future__ import annotations

import typing

from orcha import ConditionFailed
from orcha.ext import Pluggable

from .logging import Event, EventType, log

if typing.TYPE_CHECKING:
    from typing import Any, Optional

    from orcha.interfaces import Petition


def petition_track(p):
    return getattr(p, "timeline", {}).get("track", None)


def petition_render_data(p):
    return getattr(p, "timeline", {}).get("render_data", {})


class Timeline(Pluggable):
    def __init__(
        self,
        backend: str,
        priority: float = float("inf"),
        id_blacklist: list[str] = (),
    ):
        super().__init__(priority)

        assert backend in ("matplotlib",)

        self.blacklist = id_blacklist
        self.reasons = {}

    def on_timeline_event(
        self,
        type: EventType,
        name: str,
        id: Optional[str] = None,
        track: Optional[str] = None,
        render_data: dict[str, Any] = {},
        **kwargs,
    ):
        if id in self.blacklist:
            return
        event = Event(type, name, id, track, render_data, kwargs)
        log(event)

    def on_manager_start(self):
        self.on_timeline_event(
            EventType.Instant,
            "manager",
            track=None,
            render_data={"color": "dimgrey"},
            label="Orcha start",
        )

    def on_condition_check(self, p: Petition):
        self.p_id = p.id

    def on_condition_fail(self, reason: ConditionFailed):
        if self.p_id not in self.reasons or self.reasons[self.p_id] != reason.reason:
            self.on_timeline_event(
                EventType.Start, track=reason.reason, render_data=reason.environment
            )
            self.reasons[self.p_id] = reason.reasons

    def on_petition_start(self, p: Petition):
        if p.id in self.reasons:
            self.on_timeline_event(
                EventType.End,
                "wait",
                id=p.id,
                track=petition_track(p),
            )
            del self.reasons[p.id]

        self.on_timeline_event(
            EventType.Start,
            "petition",
            id=p.id,
            track=petition_track(p),
            render_data=petition_render_data(p),
        )

    def on_petition_finish(self, p: Petition):
        self.on_timeline_event(
            EventType.End,
            "petition",
            id=p.id,
            track=petition_track(p),
            status=p.state,
        )
