import json
from datetime import datetime

import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator

from .logging import EventType
from .utils import adjust_lightness


class Event:
    def __init__(
        self, type, name, id, start_ts=None, end_ts=None, render_data={}, data={}
    ):
        self.type = type
        self.name = name
        self.id = id
        self.start_ts = start_ts or 0
        self.end_ts = end_ts or float("inf")
        self.render_data = render_data
        self.data = data

    @property
    def start(self):
        try:
            return datetime.fromtimestamp(self.start_ts)
        except Exception:
            return datetime.min

    @property
    def end(self):
        try:
            return datetime.fromtimestamp(self.end_ts)
        except Exception:
            return datetime.max

    @property
    def delta(self):
        return self.end - self.start

    def overlaps(self, other):
        return (
            self.start_ts >= other.start_ts
            and self.start_ts < other.end_ts
            or self.end_ts > other.start_ts
            and self.end_ts <= other.end_ts
        )

    def __repr__(self):
        return f"Event({self.name}, {self.id}, {self.start}-{self.end})"


class Track:
    def __init__(self):
        self.subtracks = []

    def append(self, event):
        idx = None
        for i, track in enumerate(self.subtracks):
            if len(track) == 0 or all((not event.overlaps(e) for e in track)):
                idx = i
                break
        else:
            self.subtracks.append([])
            idx = -1

        self.subtracks[idx].append(event)

    def __iter__(self):
        for track in self.subtracks:
            yield track

    def __len__(self):
        return len(self.subtracks)


class Events:
    def __init__(self, tracks, start, end):
        self.tracks = tracks
        self.start = start
        self.end = end

    @property
    def n_tracks(self):
        return sum(
            len(subtracks)
            for name, subtracks in self.tracks.items()
            if name != "global"
        )


def collect_events(log_file, start=None, end=None):
    start_lim = start or datetime.max
    end_lim = end or datetime.min

    start = start or datetime.min
    end = end or datetime.max

    tracks = {}
    incomplete = {}

    with open(log_file) as f:
        for line in f.readlines():
            data = json.loads(line)
            ts = data["ts"]
            time = datetime.fromtimestamp(ts)
            if time < start or time > end:
                continue

            id = data["id"]
            type = data["type"]
            name = data["name"]
            track_name = data.get("track", None) or "global"
            render_data = data.get("render_data", {})

            if track_name not in tracks:
                tracks[track_name] = Track()
            track = tracks[track_name]

            if name == "manager":
                for event in incomplete.values():
                    event.end_ts = ts
                incomplete.clear()

            # We assume no two in-flight events have the same ID
            event = incomplete.pop(id, None)
            if event is None:
                event = Event(
                    type,
                    name,
                    id,
                    render_data=render_data,
                    data=data.get("data", {}),
                )
                track.append(event)

            if type == EventType.Start:
                event.start_ts = ts
                incomplete[id] = event
            elif type == EventType.End:
                event.end_ts = ts
            elif type == EventType.Instant:
                event.start_ts = ts
                event.end_ts = ts
            else:
                print("Invalid event type:", type)

            start_lim = min(time, start_lim)
            end_lim = max(time, end_lim)

    return Events(tracks, start_lim, end_lim)


def render_events(events, output, resolution, format):
    fig, ax = plt.subplots()

    n_track = 0
    y_locators = []
    y_ticks = []
    y_labels = []
    patches = {"global": {}, "track": {}, "wait": {}}
    for track_name, track in events.tracks.items():
        if track_name != "global":
            y_ticks.append(n_track + len(track) / 2)
            y_locators.append(n_track)
            y_labels.append(track_name)

        for subtrack in track:
            for event in subtrack:
                render_data = event.render_data
                label = event.data.get("label", "(unknown)")
                reason = event.data.get("reason", "(unknown)")

                if event.type == EventType.Instant:
                    patches["global"][label] = mpatches.Patch(
                        label=label, **render_data
                    )
                    plt.axvline(x=event.start, **render_data)
                else:
                    y = (n_track, 1)

                    if event.name == "wait":
                        opts = {"zorder": 1, **render_data}
                        patches["wait"][reason] = mpatches.Patch(label=reason, **opts)
                    else:
                        fc = render_data.get("fc", "red")
                        opts = {
                            "ec": adjust_lightness(fc, 0.75),
                            "zorder": 10,
                            **render_data,
                            "fc": fc,
                        }

                        if track_name == "global":
                            y = (0, events.n_tracks)
                            patches["global"][label] = mpatches.Patch(
                                label=label, **opts
                            )
                        else:
                            patches["track"][track_name] = mpatches.Patch(
                                label=track_name, **opts
                            )

                    ax.broken_barh([(event.start, event.delta)], y, **opts)

                if event.name == "petition":
                    ax.text(
                        event.start,
                        n_track + 0.5,
                        event.id,
                        fontsize=8,
                        va="center",
                        zorder=100,
                    )

            if track_name != "global":
                n_track += 1

    ax.set_xlim(events.start, events.end)
    ax.set_ylim(0, events.n_tracks, auto=True)

    x_locator = mdates.AutoDateLocator()
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(x_locator))
    ax.yaxis.set_minor_locator(FixedLocator(y_locators))

    ax.grid(which="minor", axis="y")
    ax.set_yticks(y_ticks, y_labels)

    fig.legend(
        handles=list(patches["global"].values())
        + list(patches["track"].values())
        + list(patches["wait"].values()),
        loc="upper right",
    )
    fig.tight_layout()

    fig.set_figwidth(resolution[0])
    fig.set_figheight(resolution[1])

    plt.savefig(output, format=format)


def render(
    log_file,
    start=None,
    end=None,
    output="timeline.png",
    resolution=(19.2, 10.8),
    format="png",
):
    events = collect_events(log_file, start, end)
    render_events(events, output, resolution, format)
