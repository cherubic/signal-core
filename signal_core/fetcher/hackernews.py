import hashlib
import logging
from datetime import datetime

import httpx

from ..models import FeedItem
from .base import BaseFetcher

logger = logging.getLogger(__name__)

HN_TOP_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{id}.json"
FETCH_COUNT = 30


class HackerNewsFetcher(BaseFetcher):
    def fetch(self) -> list[FeedItem]:
        with httpx.Client(timeout=30) as client:
            ids: list[int] = client.get(HN_TOP_URL).json()[:FETCH_COUNT]
            items: list[FeedItem] = []
            for story_id in ids:
                story: dict = client.get(HN_ITEM_URL.format(id=story_id)).json()
                url = story.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
                items.append(FeedItem(
                    id=hashlib.sha256(url.encode()).hexdigest(),
                    title=story.get("title", ""),
                    url=url,
                    source="HackerNews",
                    category="open_source",
                    published_at=datetime.fromtimestamp(story.get("time", 0)),
                    content=story.get("text", "")[:500],
                    language="en",
                ))
        return items
