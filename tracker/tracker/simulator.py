"""Synthetic readings so the whole system can be exercised without any hardware.

Each simulated child wanders between zones; when it changes floor it walks
through a ``transit`` zone (stairs) first. RSSI is modelled coarsely:

- gateway in the child's zone            ~ -58 dBm, almost always heard
- other gateway on the same floor        ~ -78 dBm, often heard
- gateway on an adjacent floor / stairs  ~ -88 dBm, sometimes heard (slabs attenuate)
- anything further                        not heard

Occasionally a child goes silent for a while (tag covered or dropped) so the
"missing" alert can be seen, and very occasionally walks into an exit zone.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .config import SiteConfig, Tag, Zone

FIRST_NAMES = [
    "Manuel", "Sofia", "Léa", "Noah", "Emma", "Luca", "Mia", "Tom", "Inês", "Ben",
    "Laura", "Max", "Clara", "Leo", "Ana", "Paul", "Eva", "Hugo", "Lina", "Rui",
    "Zoé", "Tiago", "Nora", "Félix", "Marta", "Jonas", "Alice", "David", "Lara", "Sam",
]


def simulated_tags(n: int, existing: list[Tag]) -> list[Tag]:
    """Pads ``existing`` with generated tags up to ``n`` children."""
    tags = list(existing)
    for i in range(len(tags), n):
        name = f"{FIRST_NAMES[i % len(FIRST_NAMES)]} {i // len(FIRST_NAMES) + 1}"
        tags.append(Tag(id=f"sim:{i + 1:03d}", name=name, group=f"Grupo {chr(65 + i % 6)}"))
    return tags


@dataclass
class _Kid:
    tag_id: str
    zone: Zone
    until: float
    route: list[Zone]
    silent_until: float = 0.0


class Simulator:
    def __init__(self, config: SiteConfig, seed: int | None = None,
                 lose_rate: float = 1 / 30000, exit_rate: float = 0.003):
        self.config = config
        self.rng = random.Random(seed)
        self.lose_rate = lose_rate
        self.exit_rate = exit_rate
        self._zones_by_gateway = {g.id: config.zone(g.zone) for g in config.gateways}
        covered = {g.zone for g in config.gateways}
        zones = [z for z in config.zones if z.id in covered]
        self._destinations = [z for z in zones if z.kind in ("room", "outdoor")]
        self._transit = [z for z in zones if z.kind == "transit"]
        self._exits = [z for z in zones if z.kind == "exit"]
        if not self._destinations:
            raise ValueError("simulation needs at least one room/outdoor zone with a gateway")
        self._kids: list[_Kid] = []
        self._started = False

    def _spawn(self, now: float) -> None:
        for t in self.config.tags:
            z = self.rng.choice(self._destinations)
            self._kids.append(_Kid(t.id, z, now + self.rng.uniform(5, 120), []))
        self._started = True

    def _dwell(self, zone: Zone) -> float:
        if zone.kind == "transit":
            return self.rng.uniform(4, 8)
        if zone.kind == "exit":
            return self.rng.uniform(5, 15)
        return self.rng.uniform(30, 300)

    def _next_zone(self, kid: _Kid, now: float) -> None:
        if kid.route:
            kid.zone = kid.route.pop(0)
            kid.until = now + self._dwell(kid.zone)
            return
        if self._exits and kid.zone.kind != "exit" and self.rng.random() < self.exit_rate:
            target = self.rng.choice(self._exits)
        else:
            target = self.rng.choice(self._destinations)
        if kid.zone.floor != target.floor and self._transit and target.floor is not None:
            kid.route = [target]
            kid.zone = self.rng.choice(self._transit)
        else:
            kid.zone = target
        kid.until = now + self._dwell(kid.zone)

    def _rssi(self, kid_zone: Zone, gw_zone: Zone) -> float | None:
        r = self.rng
        if gw_zone.id == kid_zone.id:
            mean, sd, p = -58, 5, 0.95
        elif kid_zone.floor is None or gw_zone.floor is None:
            mean, sd, p = -86, 4, 0.35
        elif gw_zone.floor == kid_zone.floor:
            mean, sd, p = -78, 6, 0.6
        elif abs(gw_zone.floor - kid_zone.floor) == 1:
            mean, sd, p = -89, 4, 0.25
        else:
            return None
        if r.random() > p:
            return None
        return max(-100.0, round(r.gauss(mean, sd), 1))

    def step(self, now: float) -> list[tuple[str, str, float]]:
        """One advertising round: returns (tag_id, gateway_id, rssi) readings."""
        if not self._started:
            self._spawn(now)
        readings = []
        for kid in self._kids:
            if now >= kid.until:
                self._next_zone(kid, now)
            if now < kid.silent_until:
                continue
            if self.rng.random() < self.lose_rate:
                kid.silent_until = now + self.rng.uniform(90, 180)
                continue
            for gw_id, gw_zone in self._zones_by_gateway.items():
                rssi = self._rssi(kid.zone, gw_zone)
                if rssi is not None:
                    readings.append((kid.tag_id, gw_id, rssi))
        return readings
