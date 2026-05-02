import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..models import FeedItem, SummarizedItem

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
                    title TEXT NOT NULL DEFAULT '',
                    source TEXT NOT NULL,
                    category TEXT NOT NULL,
                    summary_zh TEXT DEFAULT '',
                    is_top5 INTEGER DEFAULT 0,
                    top5_reason TEXT DEFAULT '',
                    summarized_at TEXT NOT NULL,
                    delivered INTEGER DEFAULT 0
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
        """Insert bare items without summaries (for dedup only)."""
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.executemany(
                """INSERT OR IGNORE INTO items
                   (id, url, title, source, category, summarized_at, delivered)
                   VALUES (?, ?, ?, ?, ?, ?, 0)""",
                [(i.id, i.url, getattr(i, "title", ""), i.source, i.category, now) for i in items],
            )

    def mark_summarized(self, items: list[SummarizedItem]) -> None:
        """Store items with LLM summaries; delivered flag starts at 0."""
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.executemany(
                """INSERT OR IGNORE INTO items
                   (id, url, title, source, category, summary_zh, is_top5, top5_reason, summarized_at, delivered)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
                [
                    (i.id, i.url, i.title, i.source, i.category,
                     i.summary_zh, int(i.is_top5), i.top5_reason, now)
                    for i in items
                ],
            )

    def mark_delivered(self, items: list[SummarizedItem]) -> None:
        """Mark items as successfully delivered via at least one channel."""
        with self._conn() as conn:
            conn.executemany(
                "UPDATE items SET delivered = 1 WHERE id = ?",
                [(i.id,) for i in items],
            )

    def get_pending_delivery(self) -> list[SummarizedItem]:
        """Return items that have summaries but have not been delivered yet."""
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT id, url, title, source, category, summary_zh, is_top5, top5_reason
                   FROM items WHERE delivered = 0 AND summary_zh != ''
                   ORDER BY summarized_at"""
            ).fetchall()
        return [
            SummarizedItem(
                id=row[0], url=row[1], title=row[2], source=row[3],
                category=row[4], published_at=datetime.now(timezone.utc),
                content="", language="en",
                summary_zh=row[5], is_top5=bool(row[6]), top5_reason=row[7],
            )
            for row in rows
        ]

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
            conn.execute("DELETE FROM items WHERE summarized_at < ?", (cutoff,))
