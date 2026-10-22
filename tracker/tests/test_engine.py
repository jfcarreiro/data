from pathlib import Path

import pytest

from tracker.config import SiteConfig, Tag, load_config
from tracker.engine import LocationEngine
from tracker.simulator import Simulator, simulated_tags

ROOT = Path(__file__).resolve().parents[1]


def make_config(**engine):
    return SiteConfig.model_validate({
        "name": "test",
        "floors": [{"id": 0, "name": "P0"}, {"id": 1, "name": "P1"}],
        "zones": [
            {"id": "a", "name": "A", "floor": 0},
            {"id": "b", "name": "B", "floor": 0},
            {"id": "up", "name": "Up", "floor": 1},
            {"id": "door", "name": "Door", "floor": 0, "kind": "exit"},
            {"id": "yard", "name": "Yard", "floor": 0, "kind": "outdoor"},
        ],
        "gateways": [{"id": z, "zone": z} for z in ("a", "b", "up", "door", "yard")],
        "tags": [{"id": "t1", "name": "Manuel"}, {"id": "t2", "name": "Sofia"}],
        "engine": {"switch_hold_s": 3, "switch_margin_db": 4, "missing_after_s": 60, **engine},
    })


@pytest.fixture
def engine():
    eng = LocationEngine(make_config())
    eng.events = []
    eng.subscribe(eng.events.append)
    return eng


def types(engine):
    return [e["type"] for e in engine.events]


def test_first_reading_checks_in_and_places_child(engine):
    engine.ingest("t1", "a", -60, ts=0)
    child = engine.child("t1")
    assert child["status"] == "present" and child["zone"] == "a"
    assert types(engine) == ["checked_in", "zone_enter"]


def test_switch_requires_margin_and_hold(engine):
    engine.ingest("t1", "a", -60, ts=0)
    # Slightly stronger elsewhere: within margin, stays.
    engine.ingest("t1", "b", -58, ts=1)
    assert engine.child("t1")["zone"] == "a"
    # Clearly stronger, but not for long enough yet.
    for ts in (2, 3, 4):
        engine.ingest("t1", "a", -85, ts=ts)
        engine.ingest("t1", "b", -55, ts=ts)
    assert engine.child("t1")["zone"] == "a"
    engine.ingest("t1", "b", -55, ts=6)
    assert engine.child("t1")["zone"] == "b"
    assert types(engine)[-2:] == ["zone_exit", "zone_enter"]


def test_single_spike_does_not_move_child(engine):
    for ts in range(5):
        engine.ingest("t1", "a", -60, ts=ts)
    engine.ingest("t1", "up", -50, ts=5)  # one strong reading through the slab
    for ts in range(6, 12):
        engine.ingest("t1", "a", -60, ts=ts)
    assert engine.child("t1")["zone"] == "a"


def test_stale_readings_are_ignored(engine):
    engine.ingest("t1", "a", -50, ts=0)
    # 'a' not heard for longer than the window: 'b' wins even if weaker.
    engine.ingest("t1", "b", -80, ts=20)
    engine.ingest("t1", "b", -80, ts=24)
    assert engine.child("t1")["zone"] == "b"


def test_missing_alert_and_recovery(engine):
    engine.ingest("t1", "a", -60, ts=0)
    engine.tick(30)
    assert engine.child("t1")["status"] == "present"
    engine.tick(61)
    assert engine.child("t1")["status"] == "missing"
    [alert] = engine.alerts()
    assert alert["kind"] == "missing" and alert["zone"] == "a"
    engine.tick(90)
    assert len(engine.alerts()) == 1  # no duplicate alert
    engine.ingest("t1", "a", -60, ts=100)
    assert engine.child("t1")["status"] == "present"
    assert engine.alerts() == []
    assert "found" in types(engine)


def test_exit_zone_raises_alert_until_acked(engine):
    engine.ingest("t1", "door", -60, ts=0)
    [alert] = engine.alerts()
    assert alert["kind"] == "exit"
    assert engine.ack_alert(alert["id"])
    assert engine.alerts() == []
    assert engine.alerts(active_only=False)[0]["acked"]


def test_checkout_stops_tracking_and_reset_rechecks_in(engine):
    engine.ingest("t1", "a", -60, ts=0)
    engine.check_out("t1", ts=5)
    engine.ingest("t1", "a", -60, ts=6)
    engine.tick(500)
    child = engine.child("t1")
    assert child["status"] == "checked_out" and child["zone"] is None
    assert engine.alerts() == []
    engine.reset("t1", ts=600)
    engine.ingest("t1", "b", -60, ts=601)
    assert engine.child("t1")["status"] == "present"


def test_headcount_and_zones(engine):
    engine.ingest("t1", "yard", -60, ts=0)
    engine.ingest("t2", "up", -60, ts=0)
    head = engine.headcount()
    assert head["present"] == 2 and head["outdoor"] == 1 and head["inside"] == 1
    assert head["by_floor"] == {"0": 1, "1": 1}
    zones = {z["id"]: z for z in engine.zones()}
    assert zones["up"]["children"][0]["name"] == "Sofia"


def test_unknown_tags_and_gateways_reported(engine):
    engine.ingest("phone-xyz", "a", -70, ts=0)
    engine.ingest("t1", "garage", -70, ts=0)
    health = engine.health(now=5)
    assert health["unknown_tags"][0]["id"] == "phone-xyz"
    assert health["unknown_gateways"][0]["id"] == "garage"
    assert engine.child("t1")["status"] == "absent"


def test_config_rejects_bad_references():
    with pytest.raises(ValueError):
        SiteConfig.model_validate({"name": "x", "floors": [], "zones": [],
                                   "gateways": [{"id": "g", "zone": "nope"}]})


def test_simulation_on_house_config_mostly_places_children_correctly():
    """End-to-end sanity check of the algorithm against the coarse RSSI model."""
    config = load_config(ROOT / "config" / "house.yaml")
    config.tags = simulated_tags(60, [])
    engine = LocationEngine(config)
    sim = Simulator(config, seed=1, lose_rate=0, exit_rate=0)
    agree = total = 0
    for t in range(600):
        for r in sim.step(float(t)):
            engine.ingest(*r, ts=float(t))
        engine.tick(float(t))
        if t > 60 and t % 10 == 0:
            truth = {k.tag_id: k.zone.id for k in sim._kids}
            for c in engine.children():
                total += 1
                agree += c["zone"] == truth[c["tag_id"]]
    assert agree / total > 0.85, agree / total
    floors = {c["floor"] for c in engine.children()}
    assert floors - {None} <= {0, 1, 2, 3}
