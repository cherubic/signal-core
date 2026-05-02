import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from signal_core.models import FeedItem, SummarizedItem
from signal_core.storage.db import Database


def _make_item(url: str, category: str = "ai_agent") -> FeedItem:
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


def _make_summarized(url: str, summary: str = "摘要", is_top5: bool = False) -> SummarizedItem:
    base = _make_item(url)
    return SummarizedItem(
        **vars(base),
        summary_zh=summary,
        is_top5=is_top5,
        top5_reason="重要" if is_top5 else "",
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


def test_mark_summarized_excludes_from_filter_new(db: Database):
    item = _make_summarized("https://a.com")
    db.mark_summarized([item])
    assert db.filter_new([item]) == []


def test_get_pending_delivery_returns_unsent(db: Database):
    item = _make_summarized("https://a.com", summary="test summary")
    db.mark_summarized([item])
    pending = db.get_pending_delivery()
    assert len(pending) == 1
    assert pending[0].url == "https://a.com"
    assert pending[0].summary_zh == "test summary"


def test_mark_delivered_clears_pending(db: Database):
    item = _make_summarized("https://a.com")
    db.mark_summarized([item])
    pending = db.get_pending_delivery()
    db.mark_delivered(pending)
    assert db.get_pending_delivery() == []


def test_get_pending_excludes_items_without_summary(db: Database):
    item = _make_item("https://a.com")
    db.mark_processed([item])  # no summary
    assert db.get_pending_delivery() == []


def test_save_and_retrieve_digest(db: Database):
    db.save_digest("2026-05-02", "daily content")
    assert db.get_digest("2026-05-02") == "daily content"


def test_cleanup_removes_old_items(db: Database):
    import sqlite3
    item = _make_item("https://old.com")
    db.mark_processed([item])
    old_date = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
    with sqlite3.connect(db.path) as conn:
        conn.execute("UPDATE items SET summarized_at = ?", (old_date,))
    db.cleanup_old()
    assert db.filter_new([item]) == [item]  # gone from db, treated as new
