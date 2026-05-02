from datetime import datetime
from signal_core.models import FeedItem, SummarizedItem


def _make_item(**kwargs) -> FeedItem:
    defaults = dict(
        id="abc123",
        title="Test Article",
        url="https://example.com/article",
        source="Test Blog",
        category="ai_agent",
        published_at=datetime(2026, 5, 2),
        content="Test content",
        language="en",
    )
    return FeedItem(**{**defaults, **kwargs})


def test_feed_item_fields():
    item = _make_item()
    assert item.id == "abc123"
    assert item.language == "en"
    assert item.category == "ai_agent"


def test_summarized_item_is_feed_item():
    base = _make_item()
    item = SummarizedItem(
        **vars(base),
        summary_zh="这是摘要",
        is_top5=True,
        top5_reason="非常重要",
    )
    assert isinstance(item, FeedItem)
    assert item.summary_zh == "这是摘要"
    assert item.is_top5 is True
    assert item.top5_reason == "非常重要"


def test_summarized_item_defaults():
    base = _make_item()
    item = SummarizedItem(**vars(base), summary_zh="摘要")
    assert item.is_top5 is False
    assert item.top5_reason == ""
