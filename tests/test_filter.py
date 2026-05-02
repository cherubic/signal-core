from tests.conftest import make_feed_item
from signal_core.filter.dedup import deduplicate
from signal_core.storage.db import Database


def test_deduplicate_all_new(db: Database):
    items = [make_feed_item(url=f"https://a.com/{i}") for i in range(3)]
    result = deduplicate(items, db)
    assert len(result) == 3


def test_deduplicate_removes_seen(db: Database):
    item = make_feed_item(url="https://a.com/1")
    db.mark_processed([item])
    result = deduplicate([item], db)
    assert result == []


def test_deduplicate_removes_within_batch_duplicates(db: Database):
    item = make_feed_item(url="https://a.com/1")
    # same item appearing twice in same batch (e.g. same repo in HN and GitHub)
    result = deduplicate([item, item], db)
    assert len(result) == 1
