from fastapi.testclient import TestClient

from tracker.api import Runtime, create_app
from tracker.engine import LocationEngine
from tracker.mqtt_source import parse_message
from tracker.store import EventStore

from test_engine import make_config


def make_client():
    engine = LocationEngine(make_config())
    runtime = Runtime(engine, EventStore())
    return engine, TestClient(create_app(runtime, start_background=False))


def test_endpoints_reflect_engine_state():
    engine, client = make_client()
    engine.ingest("t1", "a", -60, ts=1000)
    engine.ingest("t2", "door", -60, ts=1000)

    assert client.get("/api/site").json()["name"] == "test"
    assert [c["name"] for c in client.get("/api/children", params={"q": "man"}).json()] == ["Manuel"]
    assert client.get("/api/children/t1").json()["zone_name"] == "A"
    assert client.get("/api/children/nope").status_code == 404
    assert client.get("/api/headcount").json()["present"] == 2

    [alert] = client.get("/api/alerts").json()
    assert alert["kind"] == "exit"
    assert client.post(f"/api/alerts/{alert['id']}/ack").status_code == 200
    assert client.get("/api/alerts").json() == []

    assert client.post("/api/children/t1/checkout").json()["status"] == "checked_out"
    types = [e["type"] for e in client.get("/api/children/t1/events").json()]
    assert types[0] == "checked_out" and "zone_enter" in types
    assert client.get("/api/events").json()[0]["id"] > 1
    assert client.get("/").status_code == 200


def test_parse_message_formats():
    assert parse_message("espresense/devices/iBeacon:abc-1-1/sala", b'{"id":"iBeacon:abc-1-1","rssi":-71.5}') \
        == ("iBeacon:abc-1-1", "sala", -71.5)
    assert parse_message("tracker/readings", b'{"tag":"t1","gateway":"g1","rssi":-60}') == ("t1", "g1", -60.0)
    assert parse_message("espresense/devices/x/sala", b"not json") is None
    assert parse_message("espresense/devices/x/sala", b'{"distance": 2}') is None
    assert parse_message("espresense/rooms/sala/status", b'{"rssi": -1}') is None


def test_store_retention():
    store = EventStore()
    store.add({"ts": 1, "type": "x", "tag_id": "t", "name": "n", "zone": None})
    store.add({"ts": 100, "type": "y", "tag_id": "t", "name": "n", "zone": "a", "extra": 1})
    assert store.purge_before(50) == 1
    [e] = store.query()
    assert e["type"] == "y" and e["extra"] == 1
