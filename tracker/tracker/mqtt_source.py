"""MQTT ingestion.

Two payload formats are accepted:

- ESPresense (ESP32 receivers): topic ``espresense/devices/<device-id>/<room>``,
  JSON payload with at least ``rssi`` (and usually ``id``). ``<room>`` is the gateway id.
- Generic, for commercial gateways or custom bridges: topic ``tracker/readings``,
  JSON payload ``{"tag": "...", "gateway": "...", "rssi": -70}``.
"""

from __future__ import annotations

import json
import logging
import time

import paho.mqtt.client as mqtt

from .engine import LocationEngine

log = logging.getLogger(__name__)

ESPRESENSE_TOPIC = "espresense/devices/#"
GENERIC_TOPIC = "tracker/readings"


def parse_message(topic: str, payload: bytes) -> tuple[str, str, float] | None:
    try:
        data = json.loads(payload)
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("rssi"), (int, float)):
        return None
    if topic == GENERIC_TOPIC:
        tag, gateway = data.get("tag"), data.get("gateway")
    else:
        parts = topic.split("/")
        if len(parts) != 4 or parts[:2] != ["espresense", "devices"]:
            return None
        tag, gateway = data.get("id") or parts[2], parts[3]
    if not tag or not gateway:
        return None
    return str(tag), str(gateway), float(data["rssi"])


def _client() -> mqtt.Client:
    return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)


def _connect(client: mqtt.Client, broker: str) -> None:
    # Async connect + background loop: keeps retrying if the broker is not up yet
    # and reconnects automatically after a drop.
    host, _, port = broker.partition(":")
    client.connect_async(host, int(port or 1883))
    client.loop_start()


class MqttSource:
    def __init__(self, engine: LocationEngine, broker: str):
        self.engine = engine
        self.broker = broker
        self.client = _client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def start(self) -> None:
        _connect(self.client, self.broker)

    def stop(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        log.info("MQTT connected to %s (%s)", self.broker, reason_code)
        client.subscribe([(ESPRESENSE_TOPIC, 0), (GENERIC_TOPIC, 0)])

    def _on_message(self, client, userdata, msg):
        reading = parse_message(msg.topic, msg.payload)
        if reading:
            self.engine.ingest(*reading, ts=time.time())


class MqttPublisher:
    """Publishes simulated readings in ESPresense format, to test the MQTT path."""

    def __init__(self, broker: str):
        self.broker = broker
        self.client = _client()

    def start(self) -> None:
        _connect(self.client, self.broker)

    def stop(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()

    def publish(self, tag_id: str, gateway_id: str, rssi: float) -> None:
        self.client.publish(f"espresense/devices/{tag_id}/{gateway_id}",
                            json.dumps({"id": tag_id, "rssi": rssi}))
