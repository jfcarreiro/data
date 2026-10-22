"""Location engine: turns raw (tag, gateway, rssi) readings into zones, events and alerts.

The approach is deliberately simple ("strongest gateway wins"), because room-level
accuracy with occasional confusion between neighbouring rooms is acceptable:

1. RSSI per (tag, gateway) is smoothed with an exponential moving average.
2. Only readings from the last ``window_s`` seconds count.
3. Each zone scores the best smoothed RSSI among its gateways.
4. A child only moves to a new zone when it beats the current one by
   ``switch_margin_db`` for ``switch_hold_s`` seconds, and is heard there more
   than once (hysteresis), which prevents flapping between rooms or floors.

Time is always passed in explicitly so the engine is deterministic under test.
"""

from __future__ import annotations

import math
import threading
from collections.abc import Callable
from dataclasses import dataclass, field

from .config import SiteConfig, Tag

# absent: not detected yet today; present: in the building;
# missing: was present but no gateway hears it; checked_out: went home.
Status = str

Event = dict
Listener = Callable[[Event], None]


@dataclass
class _Signal:
    rssi: float
    ts: float


@dataclass
class _TagState:
    tag: Tag
    status: Status = "absent"
    zone: str | None = None
    zone_since: float | None = None
    last_seen: float | None = None
    signals: dict[str, _Signal] = field(default_factory=dict)
    candidate: str | None = None
    candidate_since: float | None = None
    candidate_hits: int = 0


@dataclass
class _Alert:
    id: int
    ts: float
    kind: str  # "missing" | "exit"
    tag_id: str
    name: str
    zone: str | None
    acked: bool = False
    resolved: bool = False


@dataclass
class _GatewayStats:
    last_ts: float | None = None
    readings: int = 0


class LocationEngine:
    def __init__(self, config: SiteConfig):
        self.config = config
        self.settings = config.engine
        self._lock = threading.RLock()
        self._gw_zone = {g.id: g.zone for g in config.gateways}
        self._zones = {z.id: z for z in config.zones}
        self._tags = {t.id: _TagState(t) for t in config.tags}
        self._alerts: list[_Alert] = []
        self._gateways = {g.id: _GatewayStats() for g in config.gateways}
        # Beacons heard but not registered: shown in /api/health to help setup.
        self._unknown_tags: dict[str, tuple[float, str, float]] = {}
        self._unknown_gateways: dict[str, float] = {}
        self._listeners: list[Listener] = []

    def subscribe(self, listener: Listener) -> None:
        self._listeners.append(listener)

    # ------------------------------------------------------------------ input

    def ingest(self, tag_id: str, gateway_id: str, rssi: float, ts: float) -> None:
        with self._lock:
            gw = self._gateways.get(gateway_id)
            if gw is None:
                self._unknown_gateways[gateway_id] = ts
                return
            gw.last_ts, gw.readings = ts, gw.readings + 1

            st = self._tags.get(tag_id)
            if st is None:
                self._unknown_tags[tag_id] = (ts, gateway_id, rssi)
                if len(self._unknown_tags) > 500:
                    # Phones rotate their addresses; keep only the most recent ones.
                    oldest = min(self._unknown_tags, key=lambda t: self._unknown_tags[t][0])
                    del self._unknown_tags[oldest]
                return

            sig = st.signals.get(gateway_id)
            if sig is None or ts - sig.ts > self.settings.window_s:
                st.signals[gateway_id] = _Signal(rssi, ts)
            else:
                sig.rssi += self.settings.smoothing * (rssi - sig.rssi)
                sig.ts = ts
            st.last_seen = ts

            if st.status == "checked_out":
                return
            if st.status == "absent":
                st.status = "present"
                self._emit("checked_in", ts, st)
            elif st.status == "missing":
                st.status = "present"
                self._emit("found", ts, st)
                self._resolve(st.tag.id, "missing")
            self._evaluate(st, gateway_id, ts)

    def tick(self, now: float) -> None:
        """Periodic housekeeping: detects children that stopped being heard."""
        with self._lock:
            limit = self.settings.missing_after_s
            for st in self._tags.values():
                if st.status == "present" and now - st.last_seen > limit:
                    st.status = "missing"
                    self._emit("missing", now, st, last_seen=st.last_seen)
                    self._raise("missing", now, st)

    # ------------------------------------------------------------- commands

    def check_out(self, tag_id: str, ts: float) -> None:
        with self._lock:
            st = self._tags[tag_id]
            if st.zone:
                self._emit("zone_exit", ts, st)
            st.status, st.zone, st.zone_since, st.candidate = "checked_out", None, ts, None
            self._emit("checked_out", ts, st)
            self._resolve(tag_id, None)

    def reset(self, tag_id: str, ts: float) -> None:
        """Back to 'absent' so the next detection checks the child in again."""
        with self._lock:
            st = self._tags[tag_id]
            st.status, st.zone, st.zone_since, st.candidate = "absent", None, None, None
            st.signals.clear()
            self._emit("reset", ts, st)

    def ack_alert(self, alert_id: int) -> bool:
        with self._lock:
            for a in self._alerts:
                if a.id == alert_id:
                    a.acked = True
                    return True
            return False

    # ------------------------------------------------------------ internals

    def _evaluate(self, st: _TagState, gateway_id: str, ts: float) -> None:
        window = self.settings.window_s
        for gw_id in [g for g, s in st.signals.items() if ts - s.ts > window]:
            del st.signals[gw_id]
        if not st.signals:
            return

        zone_rssi: dict[str, float] = {}
        for gw_id, sig in st.signals.items():
            z = self._gw_zone[gw_id]
            zone_rssi[z] = max(zone_rssi.get(z, -math.inf), sig.rssi)
        best = max(zone_rssi, key=zone_rssi.__getitem__)

        if st.zone is None:
            self._move(st, best, ts)
            return
        if best == st.zone:
            st.candidate = None
            return
        current = zone_rssi.get(st.zone, -math.inf)
        if zone_rssi[best] < current + self.settings.switch_margin_db:
            st.candidate = None
            return
        if st.candidate != best:
            st.candidate, st.candidate_since, st.candidate_hits = best, ts, 0
        if self._gw_zone[gateway_id] == best:
            st.candidate_hits += 1
        # A single spike (e.g. through a floor slab) stays in the window for a
        # while; requiring repeated readings keeps it from moving the child.
        if ts - st.candidate_since >= self.settings.switch_hold_s and st.candidate_hits >= 2:
            self._move(st, best, ts)

    def _move(self, st: _TagState, zone_id: str, ts: float) -> None:
        previous = st.zone
        if previous:
            self._emit("zone_exit", ts, st)
            if self._zones[previous].kind == "exit":
                self._resolve(st.tag.id, "exit")
        st.zone, st.zone_since, st.candidate = zone_id, ts, None
        self._emit("zone_enter", ts, st, from_zone=previous)
        if self._zones[zone_id].kind == "exit":
            self._raise("exit", ts, st)

    def _raise(self, kind: str, ts: float, st: _TagState) -> None:
        if any(a.tag_id == st.tag.id and a.kind == kind and not a.resolved for a in self._alerts):
            return
        alert = _Alert(len(self._alerts) + 1, ts, kind, st.tag.id, st.tag.name, st.zone)
        self._alerts.append(alert)
        self._emit("alert", ts, st, alert_id=alert.id, alert_kind=kind)

    def _resolve(self, tag_id: str, kind: str | None) -> None:
        for a in self._alerts:
            if a.tag_id == tag_id and (kind is None or a.kind == kind):
                a.resolved = True

    def _emit(self, type_: str, ts: float, st: _TagState, **extra) -> None:
        event = {"ts": ts, "type": type_, "tag_id": st.tag.id, "name": st.tag.name,
                 "zone": st.zone, **extra}
        for listener in self._listeners:
            listener(event)

    # ------------------------------------------------------------- queries

    def children(self) -> list[dict]:
        with self._lock:
            return [self._child_view(st) for st in self._tags.values()]

    def child(self, tag_id: str) -> dict | None:
        with self._lock:
            st = self._tags.get(tag_id)
            return self._child_view(st) if st else None

    def _child_view(self, st: _TagState) -> dict:
        zone = self._zones.get(st.zone) if st.zone else None
        return {
            "tag_id": st.tag.id,
            "name": st.tag.name,
            "group": st.tag.group,
            "status": st.status,
            "zone": st.zone,
            "zone_name": zone.name if zone else None,
            "floor": zone.floor if zone else None,
            "zone_since": st.zone_since,
            "last_seen": st.last_seen,
        }

    def zones(self) -> list[dict]:
        with self._lock:
            by_zone: dict[str, list[dict]] = {z.id: [] for z in self.config.zones}
            for st in self._tags.values():
                if st.zone and st.status in ("present", "missing"):
                    by_zone[st.zone].append(
                        {"tag_id": st.tag.id, "name": st.tag.name, "status": st.status})
            return [{**z.model_dump(), "count": len(by_zone[z.id]), "children": by_zone[z.id]}
                    for z in self.config.zones]

    def headcount(self) -> dict:
        with self._lock:
            counts = {"absent": 0, "present": 0, "missing": 0, "checked_out": 0}
            by_floor: dict[str, int] = {}
            outdoor = 0
            for st in self._tags.values():
                counts[st.status] += 1
                if st.status != "present" or not st.zone:
                    continue
                zone = self._zones[st.zone]
                if zone.kind == "outdoor":
                    outdoor += 1
                key = "transit" if zone.floor is None else str(zone.floor)
                by_floor[key] = by_floor.get(key, 0) + 1
            # "inside" is what matters during an evacuation.
            return {**counts, "registered": len(self._tags), "outdoor": outdoor,
                    "inside": counts["present"] - outdoor, "by_floor": by_floor}

    def alerts(self, active_only: bool = True) -> list[dict]:
        with self._lock:
            return [a.__dict__.copy() for a in self._alerts
                    if not active_only or not (a.resolved or a.acked)]

    def health(self, now: float) -> dict:
        with self._lock:
            return {
                "gateways": [{"id": g, "zone": self._gw_zone[g], "readings": s.readings,
                              "last_seen_s_ago": None if s.last_ts is None else round(now - s.last_ts, 1)}
                             for g, s in self._gateways.items()],
                "unknown_tags": [{"id": t, "last_seen_s_ago": round(now - ts, 1), "gateway": g, "rssi": r}
                                 for t, (ts, g, r) in sorted(self._unknown_tags.items(),
                                                             key=lambda kv: -kv[1][0])][:50],
                "unknown_gateways": [{"id": g, "last_seen_s_ago": round(now - ts, 1)}
                                     for g, ts in self._unknown_gateways.items()],
            }
