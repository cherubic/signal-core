import pytest
from pytest_httpx import HTTPXMock
from signal_core.fetcher.hackernews import HackerNewsFetcher

HN_TOP_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{id}.json"


def test_hn_fetcher_returns_items(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=HN_TOP_URL, json=[1001, 1002])
    httpx_mock.add_response(
        url=HN_ITEM_URL.format(id=1001),
        json={"id": 1001, "title": "Show HN: New AI Tool", "url": "https://aitool.com", "time": 1746172800},
    )
    httpx_mock.add_response(
        url=HN_ITEM_URL.format(id=1002),
        json={"id": 1002, "title": "Ask HN: Best LLM?", "time": 1746172801},
    )

    fetcher = HackerNewsFetcher()
    items = fetcher.fetch()

    assert len(items) == 2
    assert items[0].title == "Show HN: New AI Tool"
    assert items[0].url == "https://aitool.com"
    assert items[0].source == "HackerNews"
    assert items[0].language == "en"


def test_hn_fetcher_fallback_url_for_ask_hn(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=HN_TOP_URL, json=[1002])
    httpx_mock.add_response(
        url=HN_ITEM_URL.format(id=1002),
        json={"id": 1002, "title": "Ask HN: Best LLM?", "time": 1746172801},
    )

    fetcher = HackerNewsFetcher()
    items = fetcher.fetch()

    assert items[0].url == "https://news.ycombinator.com/item?id=1002"
