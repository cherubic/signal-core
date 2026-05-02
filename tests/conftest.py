import hashlib
from datetime import datetime
from pathlib import Path

import pytest

from signal_core.models import FeedItem, SummarizedItem
from signal_core.storage.db import Database


def make_feed_item(
    url: str = "https://example.com/article",
    title: str = "Test Article",
    source: str = "Test Blog",
    category: str = "ai_agent",
    content: str = "Test content about AI agents.",
    language: str = "en",
) -> FeedItem:
    return FeedItem(
        id=hashlib.sha256(url.encode()).hexdigest(),
        title=title,
        url=url,
        source=source,
        category=category,
        published_at=datetime(2026, 5, 2, 8, 0, 0),
        content=content,
        language=language,
    )


def make_summarized_item(
    url: str = "https://example.com/article",
    summary_zh: str = "这是一篇关于AI Agent的测试文章。",
    is_top5: bool = False,
    top5_reason: str = "",
    **kwargs,
) -> SummarizedItem:
    base = make_feed_item(url=url, **kwargs)
    return SummarizedItem(
        **vars(base),
        summary_zh=summary_zh,
        is_top5=is_top5,
        top5_reason=top5_reason,
    )


@pytest.fixture
def db(tmp_path: Path) -> Database:
    return Database(tmp_path / "test.db")


@pytest.fixture
def sample_items() -> list[FeedItem]:
    return [
        make_feed_item(url=f"https://example.com/{i}", title=f"Article {i}")
        for i in range(5)
    ]


@pytest.fixture
def sample_summarized() -> list[SummarizedItem]:
    items = [
        make_summarized_item(
            url=f"https://example.com/{i}",
            title=f"Article {i}",
            summary_zh=f"第{i}篇文章摘要。",
            is_top5=(i < 2),
            top5_reason="重要" if i < 2 else "",
        )
        for i in range(7)
    ]
    return items
