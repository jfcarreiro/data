"""REST API (consumed by the prototype UI and by the OutSystems app) and background loops."""

from __future__ import annotations

import logging
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .engine import LocationEngine
from .store import EventStore

log = logging.getLogger(__name__)
STATIC = Path(__file__).parent / "static"


class Runtime:
    """Owns the engine, the event store and the background threads."""

    def __init__(self, engine: LocationEngine, store: EventStore,
                 retention_s: float = 7 * 24 * 3600):
        self.engine = engine
        self.store = store
        self.retention_s = retention_s
        self.services: list = []  # objects with start()/stop(), e.g. MqttSource
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        engine.subscribe(store.add)

    def add_loop(self, fn, interval_s: float, name: str) -> None:
        """Runs ``fn(now)`` every ``interval_s`` seconds in a daemon thread."""
        def run():
            while not self._stop.is_set():
                try:
                    fn(time.time())
                except Exception:
                    log.exception("loop %s failed", name)
                self._stop.wait(interval_s)
        self._threads.append(threading.Thread(target=run, name=name, daemon=True))

    def start(self) -> None:
        self.add_loop(self.engine.tick, 1.0, "tick")
        self.add_loop(lambda now: self.store.purge_before(now - self.retention_s), 3600, "retention")
        for s in self.services:
            s.start()
        for t in self._threads:
            t.start()

    def stop(self) -> None:
        self._stop.set()
        for s in self.services:
            s.stop()


def create_app(runtime: Runtime, start_background: bool = True) -> FastAPI:
    engine, store = runtime.engine, runtime.store

    @asynccontextmanager
    async def lifespan(app):
        if start_background:
            runtime.start()
        yield
        if start_background:
            runtime.stop()

    app = FastAPI(title="Tracker API", version="0.1.0", lifespan=lifespan)
    # The OutSystems app calls this API from another origin during prototyping.
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                       allow_headers=["*"])

    def child_or_404(tag_id: str) -> dict:
        child = engine.child(tag_id)
        if child is None:
            raise HTTPException(404, f"unknown tag {tag_id!r}")
        return child

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/api/site")
    def site():
        c = engine.config
        return {"name": c.name, "floors": [f.model_dump() for f in c.floors],
                "zones": [z.model_dump() for z in c.zones],
                "gateways": [g.model_dump() for g in c.gateways]}

    @app.get("/api/children")
    def children(q: str | None = None, status: str | None = None):
        items = engine.children()
        if q:
            q = q.casefold()
            items = [c for c in items if q in c["name"].casefold()]
        if status:
            items = [c for c in items if c["status"] == status]
        return items

    @app.get("/api/children/{tag_id}")
    def child(tag_id: str):
        return child_or_404(tag_id)

    @app.get("/api/children/{tag_id}/events")
    def child_events(tag_id: str, limit: int = 100):
        child_or_404(tag_id)
        return store.query(tag_id=tag_id, limit=limit)

    @app.post("/api/children/{tag_id}/checkout")
    def checkout(tag_id: str):
        child_or_404(tag_id)
        engine.check_out(tag_id, time.time())
        return engine.child(tag_id)

    @app.post("/api/children/{tag_id}/reset")
    def reset(tag_id: str):
        child_or_404(tag_id)
        engine.reset(tag_id, time.time())
        return engine.child(tag_id)

    @app.get("/api/zones")
    def zones():
        return engine.zones()

    @app.get("/api/headcount")
    def headcount():
        return engine.headcount()

    @app.get("/api/alerts")
    def alerts(active: bool = True):
        return engine.alerts(active_only=active)

    @app.post("/api/alerts/{alert_id}/ack")
    def ack(alert_id: int):
        if not engine.ack_alert(alert_id):
            raise HTTPException(404, f"unknown alert {alert_id}")
        return {"ok": True}

    @app.get("/api/events")
    def events(since: float | None = None, limit: int = 200):
        return store.query(since=since, limit=min(limit, 1000))

    @app.get("/api/health")
    def health():
        return {"now": time.time(), **engine.health(time.time())}

    return app
