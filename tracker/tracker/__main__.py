"""Command line entry point.

    python -m tracker --config config/house.yaml --simulate 30
    python -m tracker --config config/house.yaml --mqtt localhost:1883
"""

from __future__ import annotations

import argparse
import logging

import uvicorn

from .api import Runtime, create_app
from .config import load_config
from .engine import LocationEngine
from .mqtt_source import MqttPublisher, MqttSource
from .simulator import Simulator, simulated_tags
from .store import EventStore


def main() -> None:
    p = argparse.ArgumentParser(prog="tracker", description="Prototype child location tracker")
    p.add_argument("--config", default="config/house.yaml")
    p.add_argument("--db", default="tracker.db", help="SQLite file (':memory:' for none)")
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--mqtt", metavar="HOST[:PORT]", help="MQTT broker with the receivers' readings")
    p.add_argument("--simulate", type=int, metavar="N",
                   help="simulate N children (in-process, or through --mqtt if given)")
    p.add_argument("--seed", type=int)
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    config = load_config(args.config)
    if args.simulate:
        config.tags = simulated_tags(args.simulate, config.tags)
    engine = LocationEngine(config)
    runtime = Runtime(engine, EventStore(args.db))

    if args.mqtt:
        runtime.services.append(MqttSource(engine, args.mqtt))
    if args.simulate:
        sim = Simulator(config, seed=args.seed)
        if args.mqtt:
            publisher = MqttPublisher(args.mqtt)
            runtime.services.append(publisher)
            runtime.add_loop(lambda now: [publisher.publish(*r) for r in sim.step(now)], 1.0, "sim")
        else:
            runtime.add_loop(lambda now: [engine.ingest(*r, ts=now) for r in sim.step(now)], 1.0, "sim")

    uvicorn.run(create_app(runtime), host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
