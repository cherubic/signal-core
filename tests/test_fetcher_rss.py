from unittest.mock import patch, MagicMock
from signal_core.fetcher.rss import RSSFetcher


MOCK_FEED = MagicMock()
MOCK_FEED.entries = [
    MagicMock(
        title="AI Agent Breakthrough",
        link="https://langchain.dev/post/1",
        summary="A new agent architecture...",
        published_parsed=(2026, 5, 2, 8, 0, 0, 4, 122, 0),
    ),
    MagicMock(
        title="另一篇文章",
        link="https://langchain.dev/post/2",
        summary="中文内容测试",
        published_parsed=(2026, 5, 2, 9, 0, 0, 4, 122, 0),
    ),
]


def test_rss_fetcher_returns_feed_items():
    with patch("signal_core.fetcher.rss.feedparser.parse", return_value=MOCK_FEED):
        fetcher = RSSFetcher("LangChain Blog", "https://blog.langchain.dev/rss/", "ai_agent")
        items = fetcher.fetch()
    assert len(items) == 2
    assert items[0].title == "AI Agent Breakthrough"
    assert items[0].source == "LangChain Blog"
    assert items[0].category == "ai_agent"
    assert items[0].language == "en"


def test_rss_fetcher_detects_chinese():
    with patch("signal_core.fetcher.rss.feedparser.parse", return_value=MOCK_FEED):
        fetcher = RSSFetcher("Test", "https://example.com/feed", "ai_agent")
        items = fetcher.fetch()
    assert items[1].language == "zh"


def test_rss_fetcher_id_is_url_hash():
    import hashlib
    with patch("signal_core.fetcher.rss.feedparser.parse", return_value=MOCK_FEED):
        fetcher = RSSFetcher("Test", "https://example.com/feed", "ai_agent")
        items = fetcher.fetch()
    expected_id = hashlib.sha256("https://langchain.dev/post/1".encode()).hexdigest()
    assert items[0].id == expected_id


def test_rss_fetcher_skips_entries_without_link():
    no_link_feed = MagicMock()
    no_link_feed.entries = [MagicMock(title="No link", link="", summary="")]
    no_link_feed.entries[0].get = lambda k, d="": d
    with patch("signal_core.fetcher.rss.feedparser.parse", return_value=no_link_feed):
        fetcher = RSSFetcher("Test", "https://example.com/feed", "ai_agent")
        items = fetcher.fetch()
    assert len(items) == 0
