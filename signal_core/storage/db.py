import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..models import FeedItem

RETENTION_DAYS = 30


class Database:
    def __init__(self, path: Path = Path("signal.db")):
        self.path = path
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    source TEXT NOT NULL,
                    category TEXT NOT NULL,
                    processed_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS digests (
                    date TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

    def filter_new(self, items: list[FeedItem]) -> list[FeedItem]:
        with self._conn() as conn:
            existing = {row[0] for row in conn.execute("SELECT id FROM items")}
        return [item for item in items if item.id not in existing]

    def mark_processed(self, items: list[FeedItem]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.executemany(
                "INSERT OR IGNORE INTO items (id, url, source, category, processed_at) VALUES (?, ?, ?, ?, ?)",
                [(i.id, i.url, i.source, i.category, now) for i in items],
            )

    def save_digest(self, date: str, content: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO digests (date, content, created_at) VALUES (?, ?, ?)",
                (date, content, datetime.now(timezone.utc).isoformat()),
            )

    def get_digest(self, date: str) -> str | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT content FROM digests WHERE date = ?", (date,)
            ).fetchone()
        return row[0] if row else None

    def cleanup_old(self) -> None:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)).isoformat()
        with self._conn() as conn:
            conn.execute("DELETE FROM items WHERE processed_at < ?", (cutoff,))
