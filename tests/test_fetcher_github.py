import pytest
from pytest_httpx import HTTPXMock
from signal_core.fetcher.github_trending import GitHubTrendingFetcher

GITHUB_TRENDING_URL = "https://github.com/trending?since=daily"

SAMPLE_HTML = """
<html><body>
<article class="Box-row">
  <h2 class="h3 lh-condensed">
    <a href="/someuser/awesome-llm">someuser / awesome-llm</a>
  </h2>
  <p>A curated list of LLM resources</p>
</article>
<article class="Box-row">
  <h2 class="h3 lh-condensed">
    <a href="/anotheruser/cool-agent">anotheruser / cool-agent</a>
  </h2>
  <p>An AI agent framework</p>
</article>
</body></html>
"""


def test_github_trending_fetcher_returns_items(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=GITHUB_TRENDING_URL, text=SAMPLE_HTML)
    fetcher = GitHubTrendingFetcher()
    items = fetcher.fetch()

    assert len(items) == 2
    assert items[0].title == "someuser / awesome-llm"
    assert items[0].url == "https://github.com/someuser/awesome-llm"
    assert items[0].source == "GitHub Trending"
    assert items[0].content == "A curated list of LLM resources"
    assert items[0].language == "en"


def test_github_trending_id_is_url_hash(httpx_mock: HTTPXMock):
    import hashlib
    httpx_mock.add_response(url=GITHUB_TRENDING_URL, text=SAMPLE_HTML)
    fetcher = GitHubTrendingFetcher()
    items = fetcher.fetch()
    expected = hashlib.sha256("https://github.com/someuser/awesome-llm".encode()).hexdigest()
    assert items[0].id == expected
