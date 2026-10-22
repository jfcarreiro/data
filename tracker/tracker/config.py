"""Site configuration: floors, zones, gateways (receivers) and registered tags."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

ZoneKind = Literal["room", "transit", "outdoor", "exit"]


class Floor(BaseModel):
    id: int
    name: str


class Zone(BaseModel):
    id: str
    name: str
    # None for zones that span floors (e.g. a stairwell).
    floor: int | None = None
    # "exit" zones raise an alert when a present child is detected there.
    kind: ZoneKind = "room"


class Gateway(BaseModel):
    # Must match the receiver's name (for ESPresense: the configured "room" name).
    id: str
    zone: str


class Tag(BaseModel):
    # Beacon id as reported by the gateway, e.g. "iBeacon:<uuid>-<major>-<minor>".
    id: str
    name: str
    group: str | None = None


class EngineSettings(BaseModel):
    # Readings older than this are ignored when deciding the zone.
    window_s: float = 15.0
    # Exponential smoothing factor for RSSI (0 < a <= 1; higher reacts faster).
    smoothing: float = Field(0.3, gt=0, le=1)
    # A new zone must beat the current one by this many dB...
    switch_margin_db: float = 4.0
    # ...for at least this long before the child is moved.
    switch_hold_s: float = 3.0
    # A present child not heard by any gateway for this long raises an alert.
    missing_after_s: float = 60.0


class SiteConfig(BaseModel):
    name: str
    floors: list[Floor]
    zones: list[Zone]
    gateways: list[Gateway]
    tags: list[Tag] = []
    engine: EngineSettings = EngineSettings()

    @model_validator(mode="after")
    def _check_references(self) -> SiteConfig:
        floor_ids = {f.id for f in self.floors}
        zone_ids = [z.id for z in self.zones]
        for label, ids in (
            ("floor", [f.id for f in self.floors]),
            ("zone", zone_ids),
            ("gateway", [g.id for g in self.gateways]),
            ("tag", [t.id for t in self.tags]),
        ):
            dupes = {i for i in ids if ids.count(i) > 1}
            if dupes:
                raise ValueError(f"duplicate {label} ids: {sorted(map(str, dupes))}")
        for z in self.zones:
            if z.floor is not None and z.floor not in floor_ids:
                raise ValueError(f"zone {z.id!r} references unknown floor {z.floor}")
        for g in self.gateways:
            if g.zone not in zone_ids:
                raise ValueError(f"gateway {g.id!r} references unknown zone {g.zone!r}")
        return self

    def zone(self, zone_id: str) -> Zone:
        return next(z for z in self.zones if z.id == zone_id)


def load_config(path: str | Path) -> SiteConfig:
    with open(path, encoding="utf-8") as f:
        return SiteConfig.model_validate(yaml.safe_load(f))
