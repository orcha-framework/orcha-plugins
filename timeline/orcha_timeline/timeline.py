from __future__ import annotations

import typing

from orcha.lib.pluggable import Pluggable

from .logging import Event, EventType, log

if typing.TYPE_CHECKING:
    from typing import Any, Optional

    from orcha.interfaces import Petition
    from orcha.interfaces.types import Bool


class ConditionError(Exception):
    def __init__(self, missing: str):
        super().__init__(f"Condition is missing {missing} to succeed")
        self.missing = missing

    @property
    def reason(self):
        return f"Waiting for {self.missing}"

    @property
    def ec(self):
        return None

    @property
    def fc(self):
        return None

    @property
    def hatch(self):
        return None

    def __bool__(self):
        return False

    def render_data(self):
        return {
            "ec": self.ec,
            "fc": self.fc,
            "hatch": self.hatch,
        }


def petition_track(p):
    return getattr(p, "timeline", {}).get("track", None)


def petition_render_data(p):
    return getattr(p, "timeline", {}).get("render_data", {})


class Timeline(Pluggable):
    def __init__(
        self,
        priority: float = float("inf"),
        id_blacklist: list[str] = (),
    ):
        super().__init__(priority)

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

    def on_petition_start(self, p: Petition):
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

    def on_petition_check(self, p: Petition, result: Bool):
        if result:
            reason = None
        elif isinstance(result, ConditionError):
            reason = result.reason
            render_data = result.render_data()
        else:
            reason = "(unknown)"
            render_data = {}
        prev_reason = self.reasons.get(p.id, None)

        if prev_reason != reason:
            if prev_reason is not None:
                del self.reasons[p.id]
                self.on_timeline_event(
                    EventType.End,
                    "wait",
                    id=p.id,
                    track=petition_track(p),
                )

            if reason is not None:
                self.reasons[p.id] = reason
                self.on_timeline_event(
                    EventType.Start,
                    "wait",
                    id=p.id,
                    track=petition_track(p),
                    reason=reason,
                    render_data=render_data,
                )

        return result
