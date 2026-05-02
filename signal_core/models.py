from dataclasses import dataclass
from datetime import datetime


@dataclass
class FeedItem:
    id: str
    title: str
    url: str
    source: str
    category: str
    published_at: datetime
    content: str
    language: str


@dataclass
class SummarizedItem(FeedItem):
    summary_zh: str = ""
    is_top5: bool = False
    top5_reason: str = ""
