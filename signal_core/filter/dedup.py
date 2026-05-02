from ..models import FeedItem
from ..storage.db import Database


def deduplicate(items: list[FeedItem], db: Database) -> list[FeedItem]:
    seen: set[str] = set()
    unique: list[FeedItem] = []
    for item in items:
        if item.id not in seen:
            seen.add(item.id)
            unique.append(item)
    return db.filter_new(unique)
