import hashlib
import logging
from datetime import datetime

import feedparser

from ..models import FeedItem
from .base import BaseFetcher

logger = logging.getLogger(__name__)
MAX_ITEMS_PER_SOURCE = 20


class RSSFetcher(BaseFetcher):
    def __init__(self, name: str, url: str, category: str):
        self.name = name
        self.url = url
        self.category = category

    def fetch(self) -> list[FeedItem]:
        feed = feedparser.parse(self.url)
        items: list[FeedItem] = []
        for entry in feed.entries[:MAX_ITEMS_PER_SOURCE]:
            url = self._get_entry_field(entry, "link", "")
            if not url:
                continue
            items.append(FeedItem(
                id=hashlib.sha256(url.encode()).hexdigest(),
                title=self._get_entry_field(entry, "title", ""),
                url=url,
                source=self.name,
                category=self.category,
                published_at=self._parse_date(entry),
                content=self._get_entry_field(entry, "summary", "")[:500],
                language=self._detect_language(self._get_entry_field(entry, "title", "")),
            ))
        return items

    def _get_entry_field(self, entry: object, field: str, default: str = "") -> str:
        """Get a field from an entry, supporting both dict and object access."""
        # Try attribute access first (works for both feedparser entries and mocks)
        value = getattr(entry, field, None)
        if value is None:
            # Fall back to dict-like access
            try:
                value = entry.get(field, default)
            except (AttributeError, TypeError):
                value = default
        return value if isinstance(value, str) else default

    def _parse_date(self, entry: object) -> datetime:
        parsed = getattr(entry, "published_parsed", None)
        if parsed:
            return datetime(*parsed[:6])
        return datetime.utcnow()

    def _detect_language(self, text: str) -> str:
        if not text:
            return "en"
        cjk_count = sum(1 for c in text if "一" <= c <= "鿿")
        return "zh" if cjk_count / len(text) > 0.1 else "en"
