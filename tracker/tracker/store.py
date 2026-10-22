"""SQLite event log. Only state changes are stored, never the raw readings."""

from __future__ import annotations

import json
import sqlite3
import threading

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    type TEXT NOT NULL,
    tag_id TEXT NOT NULL,
    name TEXT NOT NULL,
    zone TEXT,
    data TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS events_ts ON events (ts);
CREATE INDEX IF NOT EXISTS events_tag ON events (tag_id, ts);
"""

_COLUMNS = ("ts", "type", "tag_id", "name", "zone")


class EventStore:
    def __init__(self, path: str = ":memory:"):
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.executescript(_SCHEMA)
        self._lock = threading.Lock()

    def add(self, event: dict) -> None:
        extra = {k: v for k, v in event.items() if k not in _COLUMNS}
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO events (ts, type, tag_id, name, zone, data) VALUES (?, ?, ?, ?, ?, ?)",
                (*(event.get(c) for c in _COLUMNS), json.dumps(extra)),
            )

    def query(self, since: float | None = None, tag_id: str | None = None,
              limit: int = 200) -> list[dict]:
        sql, args = "SELECT * FROM events WHERE 1=1", []
        if since is not None:
            sql += " AND ts > ?"
            args.append(since)
        if tag_id is not None:
            sql += " AND tag_id = ?"
            args.append(tag_id)
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        with self._lock:
            rows = self._db.execute(sql, args).fetchall()
        return [{"id": r["id"], **{c: r[c] for c in _COLUMNS}, **json.loads(r["data"])}
                for r in rows]

    def purge_before(self, ts: float) -> int:
        """Retention: delete events older than ``ts`` (GDPR: keep location history short)."""
        with self._lock, self._db:
            return self._db.execute("DELETE FROM events WHERE ts < ?", (ts,)).rowcount
