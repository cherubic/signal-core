from datetime import datetime, timezone
from pathlib import Path
import pytest
from signal_core.models import FeedItem
from signal_core.storage.db import Database


def _make_item(url: str, category: str = "ai_agent") -> FeedItem:
    import hashlib
    return FeedItem(
        id=hashlib.sha256(url.encode()).hexdigest(),
        title="Test",
        url=url,
        source="Test",
        category=category,
        published_at=datetime(2026, 5, 2),
        content="content",
        language="en",
    )


@pytest.fixture
def db(tmp_path: Path) -> Database:
    return Database(tmp_path / "test.db")


def test_filter_new_returns_all_when_empty(db: Database):
    items = [_make_item("https://a.com"), _make_item("https://b.com")]
    assert db.filter_new(items) == items


def test_filter_new_excludes_processed(db: Database):
    item = _make_item("https://a.com")
    db.mark_processed([item])
    assert db.filter_new([item]) == []


def test_filter_new_partial(db: Database):
    item_a = _make_item("https://a.com")
    item_b = _make_item("https://b.com")
    db.mark_processed([item_a])
    result = db.filter_new([item_a, item_b])
    assert result == [item_b]


def test_save_and_retrieve_digest(db: Database):
    db.save_digest("2026-05-02", "daily content")
    assert db.get_digest("2026-05-02") == "daily content"


def test_cleanup_removes_old_items(db: Database):
    from datetime import timedelta
    item = _make_item("https://old.com")
    db.mark_processed([item])
    import sqlite3
    old_date = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
    with sqlite3.connect(db.path) as conn:
        conn.execute("UPDATE items SET processed_at = ?", (old_date,))
    db.cleanup_old()
    assert db.filter_new([item]) == [item]  # gone from db, so treated as new
