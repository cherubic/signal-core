from pathlib import Path
import pytest
from signal_core.config import SourceConfig, load_sources


SAMPLE_YAML = """
sources:
  - name: "Test RSS"
    url: "https://example.com/feed.xml"
    type: rss
    category: ai_agent
  - name: "HackerNews"
    type: hackernews_api
    category: open_source
  - name: "GitHub Trending"
    url: "https://github.com/trending"
    type: github_trending
    category: open_source
"""


@pytest.fixture
def yaml_file(tmp_path: Path) -> Path:
    p = tmp_path / "sources.yaml"
    p.write_text(SAMPLE_YAML)
    return p


def test_load_sources_returns_list(yaml_file: Path):
    sources = load_sources(yaml_file)
    assert len(sources) == 3


def test_load_sources_rss_fields(yaml_file: Path):
    sources = load_sources(yaml_file)
    rss = sources[0]
    assert rss.name == "Test RSS"
    assert rss.url == "https://example.com/feed.xml"
    assert rss.type == "rss"
    assert rss.category == "ai_agent"


def test_load_sources_no_url_for_api_type(yaml_file: Path):
    sources = load_sources(yaml_file)
    hn = sources[1]
    assert hn.type == "hackernews_api"
    assert hn.url == ""
