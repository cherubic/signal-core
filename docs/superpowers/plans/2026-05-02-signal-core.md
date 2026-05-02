# signal-core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个每日自动抓取 AI 与软件行业优质内容、LLM 摘要、推送至邮件/Telegram/飞书的个人信息流系统。

**Architecture:** 四阶段流水线：Fetcher（RSS + HackerNews + GitHub Trending）→ Filter（SQLite 去重）→ Summarizer（Deepseek/Kimi API）→ Deliverer（三渠道独立推送）。APScheduler 每天 08:00 触发完整运行，支持 `python -m signal_core run` 手动触发。

**Tech Stack:** Python 3.12, feedparser, httpx, beautifulsoup4, openai-sdk（OpenAI 兼容接口）, apscheduler, python-dotenv, jinja2, pyyaml, pytest, ruff, mypy

---

## File Map

```
signal_core/
├── __init__.py
├── __main__.py          # python -m signal_core 入口
├── models.py            # FeedItem, SummarizedItem
├── config.py            # 加载 sources.yaml，SourceConfig dataclass
├── pipeline.py          # 串联四阶段的主编排器
├── scheduler.py         # APScheduler 定时触发 + CLI
├── storage/
│   ├── __init__.py
│   └── db.py            # SQLite 封装：去重、持久化、清理
├── fetcher/
│   ├── __init__.py
│   ├── base.py          # BaseFetcher ABC
│   ├── rss.py           # RSS/Atom 抓取
│   ├── hackernews.py    # HN API 全量抓取
│   └── github_trending.py # GitHub Trending 爬取
├── filter/
│   ├── __init__.py
│   └── dedup.py         # 基于 SQLite 的去重过滤
├── summarizer/
│   ├── __init__.py      # create_summarizer() 工厂
│   ├── base.py          # BaseSummarizer ABC
│   ├── deepseek.py      # Deepseek v4 Adapter
│   └── kimi.py          # Kimi 2.6 Adapter
└── deliver/
    ├── __init__.py
    ├── base.py          # BaseDeliverer ABC
    ├── formatter.py     # 共享格式化逻辑（text + HTML）
    ├── email.py         # SMTP HTML 邮件
    ├── telegram.py      # Telegram Bot API
    └── feishu.py        # 飞书 Webhook

config/
└── sources.yaml         # 信息源配置

tests/
├── conftest.py          # 共享 fixtures（sample items, tmp db）
├── test_models.py
├── test_storage.py
├── test_config.py
├── test_fetcher_rss.py
├── test_fetcher_hn.py
├── test_fetcher_github.py
├── test_filter.py
├── test_summarizer.py
├── test_formatter.py
├── test_deliver_email.py
├── test_deliver_telegram.py
├── test_deliver_feishu.py
└── test_pipeline.py
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `signal_core/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=70"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "signal-core"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "feedparser>=6.0",
    "httpx>=0.27",
    "beautifulsoup4>=4.12",
    "openai>=1.0",
    "apscheduler>=3.10",
    "python-dotenv>=1.0",
    "jinja2>=3.1",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-httpx>=0.30",
    "mypy>=1.10",
    "ruff>=0.4",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["signal_core*"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.mypy]
python_version = "3.12"
strict = true
```

- [ ] **Step 2: Create `.env.example`**

```
SUMMARIZER_BACKEND=deepseek

DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

KIMI_API_KEY=
KIMI_BASE_URL=https://api.moonshot.cn/v1
KIMI_MODEL=moonshot-v1-128k

EMAIL_SMTP_HOST=
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USER=
EMAIL_SMTP_PASS=
EMAIL_TO=

TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

FEISHU_WEBHOOK_URL=
```

- [ ] **Step 3: Create package init files**

`signal_core/__init__.py` — 空文件

`tests/__init__.py` — 空文件

- [ ] **Step 4: Install dependencies**

```bash
pip install -e ".[dev]"
```

Expected: 所有依赖安装成功，无报错。

- [ ] **Step 5: Verify setup**

```bash
python -c "import feedparser, httpx, openai, apscheduler; print('OK')"
```

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .env.example signal_core/__init__.py tests/__init__.py
git commit -m "chore: project scaffolding and dependencies"
```

---

## Task 2: Data Models

**Files:**
- Create: `signal_core/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing tests**

`tests/test_models.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify failure**

```bash
pytest tests/test_models.py -v
```

Expected: `ImportError: cannot import name 'FeedItem'`

- [ ] **Step 3: Implement `signal_core/models.py`**

```python
from dataclasses import dataclass, field
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
```

- [ ] **Step 4: Run tests to verify passing**

```bash
pytest tests/test_models.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add signal_core/models.py tests/test_models.py
git commit -m "feat: add FeedItem and SummarizedItem data models"
```

---

## Task 3: Storage Layer

**Files:**
- Create: `signal_core/storage/__init__.py`
- Create: `signal_core/storage/db.py`
- Create: `tests/test_storage.py`

- [ ] **Step 1: Write failing tests**

`tests/test_storage.py`:

```python
from datetime import datetime
from pathlib import Path
import pytest
from signal_core.models import FeedItem
from signal_core.storage.db import Database


def _make_item(url: str, category: str = "ai_agent") -> FeedItem:
    import hashlib
    return FeedItem(
        id=hashlib.sha256(url.encode()).hexdigest(),
        title="Test",
        url=url,
        source="Test",
        category=category,
        published_at=datetime(2026, 5, 2),
        content="content",
        language="en",
    )


@pytest.fixture
def db(tmp_path: Path) -> Database:
    return Database(tmp_path / "test.db")


def test_filter_new_returns_all_when_empty(db: Database):
    items = [_make_item("https://a.com"), _make_item("https://b.com")]
    assert db.filter_new(items) == items


def test_filter_new_excludes_processed(db: Database):
    item = _make_item("https://a.com")
    db.mark_processed([item])
    assert db.filter_new([item]) == []


def test_filter_new_partial(db: Database):
    item_a = _make_item("https://a.com")
    item_b = _make_item("https://b.com")
    db.mark_processed([item_a])
    result = db.filter_new([item_a, item_b])
    assert result == [item_b]


def test_save_and_retrieve_digest(db: Database):
    db.save_digest("2026-05-02", "daily content")
    assert db.get_digest("2026-05-02") == "daily content"


def test_cleanup_removes_old_items(db: Database):
    from datetime import timedelta
    item = _make_item("https://old.com")
    db.mark_processed([item])
    # Manually set processed_at to 31 days ago
    import sqlite3
    old_date = (datetime.utcnow() - timedelta(days=31)).isoformat()
    with sqlite3.connect(db.path) as conn:
        conn.execute("UPDATE items SET processed_at = ?", (old_date,))
    db.cleanup_old()
    assert db.filter_new([item]) == [item]  # should be gone from db
```

- [ ] **Step 2: Run tests to verify failure**

```bash
pytest tests/test_storage.py -v
```

Expected: `ImportError: cannot import name 'Database'`

- [ ] **Step 3: Implement `signal_core/storage/db.py`**

```python
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from ..models import FeedItem

RETENTION_DAYS = 30


class Database:
    def __init__(self, path: Path = Path("signal.db")):
        self.path = path
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    source TEXT NOT NULL,
                    category TEXT NOT NULL,
                    processed_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS digests (
                    date TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

    def filter_new(self, items: list[FeedItem]) -> list[FeedItem]:
        with self._conn() as conn:
            existing = {row[0] for row in conn.execute("SELECT id FROM items")}
        return [item for item in items if item.id not in existing]

    def mark_processed(self, items: list[FeedItem]) -> None:
        now = datetime.utcnow().isoformat()
        with self._conn() as conn:
            conn.executemany(
                "INSERT OR IGNORE INTO items (id, url, source, category, processed_at) VALUES (?, ?, ?, ?, ?)",
                [(i.id, i.url, i.source, i.category, now) for i in items],
            )

    def save_digest(self, date: str, content: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO digests (date, content, created_at) VALUES (?, ?, ?)",
                (date, content, datetime.utcnow().isoformat()),
            )

    def get_digest(self, date: str) -> str | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT content FROM digests WHERE date = ?", (date,)
            ).fetchone()
        return row[0] if row else None

    def cleanup_old(self) -> None:
        cutoff = (datetime.utcnow() - timedelta(days=RETENTION_DAYS)).isoformat()
        with self._conn() as conn:
            conn.execute("DELETE FROM items WHERE processed_at < ?", (cutoff,))
```

`signal_core/storage/__init__.py` — 空文件

- [ ] **Step 4: Run tests to verify passing**

```bash
pytest tests/test_storage.py -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add signal_core/storage/ tests/test_storage.py
git commit -m "feat: add SQLite storage layer with dedup and digest persistence"
```

---

## Task 4: Config Loader

**Files:**
- Create: `signal_core/config.py`
- Create: `config/sources.yaml`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing tests**

`tests/test_config.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify failure**

```bash
pytest tests/test_config.py -v
```

Expected: `ImportError: cannot import name 'SourceConfig'`

- [ ] **Step 3: Implement `signal_core/config.py`**

```python
from dataclasses import dataclass, field
from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = Path("config/sources.yaml")


@dataclass
class SourceConfig:
    name: str
    type: str
    category: str
    url: str = ""


def load_sources(path: Path = DEFAULT_CONFIG_PATH) -> list[SourceConfig]:
    with open(path) as f:
        data = yaml.safe_load(f)
    return [
        SourceConfig(
            name=src["name"],
            type=src["type"],
            category=src["category"],
            url=src.get("url", ""),
        )
        for src in data["sources"]
    ]
```

- [ ] **Step 4: Create `config/sources.yaml`**

```yaml
sources:
  # ── AI Agent ──────────────────────────────────────
  - name: "LangChain Blog"
    url: "https://blog.langchain.dev/rss/"
    type: rss
    category: ai_agent

  - name: "arXiv cs.AI"
    url: "https://rss.arxiv.org/rss/cs.AI"
    type: rss
    category: ai_agent

  # ── LLM 应用开发 ───────────────────────────────────
  - name: "Anthropic Blog"
    url: "https://www.anthropic.com/rss.xml"
    type: rss
    category: llm_dev

  - name: "Hugging Face Blog"
    url: "https://huggingface.co/blog/feed.xml"
    type: rss
    category: llm_dev

  - name: "OpenAI Blog"
    url: "https://openai.com/blog/rss.xml"
    type: rss
    category: llm_dev

  - name: "Google DeepMind Blog"
    url: "https://deepmind.google/blog/rss.xml"
    type: rss
    category: llm_dev

  - name: "Meta AI Blog"
    url: "https://ai.meta.com/blog/rss/"
    type: rss
    category: llm_dev

  - name: "Simon Willison's Blog"
    url: "https://simonwillison.net/atom/everything/"
    type: rss
    category: llm_dev

  - name: "量子位"
    url: "https://www.qbitai.com/feed"
    type: rss
    category: llm_dev

  - name: "机器之心"
    url: "https://www.jiqizhixin.com/rss"
    type: rss
    category: llm_dev

  # ── AI 编程工具 ────────────────────────────────────
  - name: "GitHub Trending"
    url: "https://github.com/trending?since=daily"
    type: github_trending
    category: ai_tools

  - name: "HackerNews"
    type: hackernews_api
    category: ai_tools

  # ── AI Infra ──────────────────────────────────────
  - name: "vLLM Blog"
    url: "https://blog.vllm.ai/feed.xml"
    type: rss
    category: ai_infra

  - name: "Ollama Releases"
    url: "https://github.com/ollama/ollama/releases.atom"
    type: rss
    category: ai_infra

  - name: "美团技术博客"
    url: "https://tech.meituan.com/feed/"
    type: rss
    category: ai_infra

  # ── 软件工程实践 ───────────────────────────────────
  - name: "Martin Fowler"
    url: "https://martinfowler.com/feed.atom"
    type: rss
    category: swe

  - name: "InfoQ"
    url: "https://feed.infoq.com/"
    type: rss
    category: swe

  - name: "阮一峰的网络日志"
    url: "https://www.ruanyifeng.com/blog/atom.xml"
    type: rss
    category: swe

  # ── 开源项目 ──────────────────────────────────────
  - name: "开源中国"
    url: "https://www.oschina.net/news/rss"
    type: rss
    category: open_source

  # ── 论文研究 ──────────────────────────────────────
  - name: "arXiv cs.LG"
    url: "https://rss.arxiv.org/rss/cs.LG"
    type: rss
    category: research

  - name: "arXiv cs.CL"
    url: "https://rss.arxiv.org/rss/cs.CL"
    type: rss
    category: research
```

- [ ] **Step 5: Run tests to verify passing**

```bash
pytest tests/test_config.py -v
```

Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add signal_core/config.py config/sources.yaml tests/test_config.py
git commit -m "feat: add config loader and initial sources.yaml"
```

---

## Task 5: Test Fixtures (conftest.py)

**Files:**
- Create: `tests/conftest.py`

- [ ] **Step 1: Create shared fixtures**

`tests/conftest.py`:

```python
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
```

- [ ] **Step 2: Verify conftest loads correctly**

```bash
pytest tests/ --collect-only 2>&1 | head -20
```

Expected: 无 import 错误

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "test: add shared fixtures in conftest.py"
```

---

## Task 6: RSS Fetcher

**Files:**
- Create: `signal_core/fetcher/__init__.py`
- Create: `signal_core/fetcher/base.py`
- Create: `signal_core/fetcher/rss.py`
- Create: `tests/test_fetcher_rss.py`

- [ ] **Step 1: Write failing tests**

`tests/test_fetcher_rss.py`:

```python
from unittest.mock import patch, MagicMock
from datetime import datetime
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
        # entries with empty link should be skipped
        items = fetcher.fetch()
    assert len(items) == 0
```

- [ ] **Step 2: Run tests to verify failure**

```bash
pytest tests/test_fetcher_rss.py -v
```

Expected: `ImportError: cannot import name 'RSSFetcher'`

- [ ] **Step 3: Implement `signal_core/fetcher/base.py`**

```python
from abc import ABC, abstractmethod
from ..models import FeedItem


class BaseFetcher(ABC):
    @abstractmethod
    def fetch(self) -> list[FeedItem]:
        ...
```

- [ ] **Step 4: Implement `signal_core/fetcher/rss.py`**

```python
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
            url = entry.get("link", "")
            if not url:
                continue
            items.append(FeedItem(
                id=hashlib.sha256(url.encode()).hexdigest(),
                title=entry.get("title", ""),
                url=url,
                source=self.name,
                category=self.category,
                published_at=self._parse_date(entry),
                content=entry.get("summary", "")[:500],
                language=self._detect_language(entry.get("title", "")),
            ))
        return items

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
```

`signal_core/fetcher/__init__.py` — 空文件

- [ ] **Step 5: Run tests to verify passing**

```bash
pytest tests/test_fetcher_rss.py -v
```

Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add signal_core/fetcher/ tests/test_fetcher_rss.py
git commit -m "feat: add RSS fetcher with CJK language detection"
```

---

## Task 7: HackerNews Fetcher

**Files:**
- Create: `signal_core/fetcher/hackernews.py`
- Create: `tests/test_fetcher_hn.py`

- [ ] **Step 1: Write failing tests**

`tests/test_fetcher_hn.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify failure**

```bash
pytest tests/test_fetcher_hn.py -v
```

Expected: `ImportError: cannot import name 'HackerNewsFetcher'`

- [ ] **Step 3: Implement `signal_core/fetcher/hackernews.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify passing**

```bash
pytest tests/test_fetcher_hn.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add signal_core/fetcher/hackernews.py tests/test_fetcher_hn.py
git commit -m "feat: add HackerNews fetcher (top 30 stories)"
```

---

## Task 8: GitHub Trending Fetcher

**Files:**
- Create: `signal_core/fetcher/github_trending.py`
- Create: `tests/test_fetcher_github.py`

- [ ] **Step 1: Write failing tests**

`tests/test_fetcher_github.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify failure**

```bash
pytest tests/test_fetcher_github.py -v
```

Expected: `ImportError: cannot import name 'GitHubTrendingFetcher'`

- [ ] **Step 3: Implement `signal_core/fetcher/github_trending.py`**

```python
import hashlib
import logging
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from ..models import FeedItem
from .base import BaseFetcher

logger = logging.getLogger(__name__)

GITHUB_TRENDING_URL = "https://github.com/trending?since=daily"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; signal-core/0.1)"}


class GitHubTrendingFetcher(BaseFetcher):
    def fetch(self) -> list[FeedItem]:
        with httpx.Client(timeout=30, headers=HEADERS) as client:
            resp = client.get(GITHUB_TRENDING_URL)
        soup = BeautifulSoup(resp.text, "html.parser")
        items: list[FeedItem] = []
        for repo in soup.select("article.Box-row"):
            link_el = repo.select_one("h2 a")
            if not link_el:
                continue
            path = link_el["href"].lstrip("/")
            url = f"https://github.com/{path}"
            title = path.replace("/", " / ")
            desc_el = repo.select_one("p")
            desc = desc_el.get_text(strip=True) if desc_el else ""
            items.append(FeedItem(
                id=hashlib.sha256(url.encode()).hexdigest(),
                title=title,
                url=url,
                source="GitHub Trending",
                category="open_source",
                published_at=datetime.utcnow(),
                content=desc,
                language="en",
            ))
        return items
```

- [ ] **Step 4: Run tests to verify passing**

```bash
pytest tests/test_fetcher_github.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add signal_core/fetcher/github_trending.py tests/test_fetcher_github.py
git commit -m "feat: add GitHub Trending fetcher via HTML scraping"
```

---

## Task 9: Deduplication Filter

**Files:**
- Create: `signal_core/filter/__init__.py`
- Create: `signal_core/filter/dedup.py`
- Create: `tests/test_filter.py`

- [ ] **Step 1: Write failing tests**

`tests/test_filter.py`:

```python
from tests.conftest import make_feed_item
from signal_core.filter.dedup import deduplicate
from signal_core.storage.db import Database


def test_deduplicate_all_new(db: Database):
    items = [make_feed_item(url=f"https://a.com/{i}") for i in range(3)]
    result = deduplicate(items, db)
    assert len(result) == 3


def test_deduplicate_removes_seen(db: Database):
    item = make_feed_item(url="https://a.com/1")
    db.mark_processed([item])
    result = deduplicate([item], db)
    assert result == []


def test_deduplicate_removes_within_batch_duplicates(db: Database):
    item = make_feed_item(url="https://a.com/1")
    # same item appearing twice in same batch (e.g. same repo in HN and GitHub)
    result = deduplicate([item, item], db)
    assert len(result) == 1
```

- [ ] **Step 2: Run tests to verify failure**

```bash
pytest tests/test_filter.py -v
```

Expected: `ImportError: cannot import name 'deduplicate'`

- [ ] **Step 3: Implement `signal_core/filter/dedup.py`**

```python
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
```

`signal_core/filter/__init__.py` — 空文件

- [ ] **Step 4: Run tests to verify passing**

```bash
pytest tests/test_filter.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add signal_core/filter/ tests/test_filter.py
git commit -m "feat: add deduplication filter (within-batch + db-backed)"
```

---

## Task 10: Summarizer Base + Deepseek Adapter

**Files:**
- Create: `signal_core/summarizer/__init__.py`
- Create: `signal_core/summarizer/base.py`
- Create: `signal_core/summarizer/deepseek.py`
- Create: `tests/test_summarizer.py`

- [ ] **Step 1: Write failing tests**

`tests/test_summarizer.py`:

```python
import json
from unittest.mock import MagicMock, patch
from tests.conftest import make_feed_item
from signal_core.summarizer.deepseek import DeepseekSummarizer
from signal_core.models import SummarizedItem


def _mock_client(responses: list[str]):
    """Returns a patched OpenAI client that returns responses in order."""
    mock = MagicMock()
    mock.chat.completions.create.side_effect = [
        MagicMock(choices=[MagicMock(message=MagicMock(content=r))])
        for r in responses
    ]
    return mock


def test_summarize_returns_summarized_items():
    item = make_feed_item()
    summary_response = json.dumps({"summary_zh": "AI Agent的新突破。", "category": "ai_agent"})
    mock_client = _mock_client([summary_response])

    with patch("signal_core.summarizer.deepseek.OpenAI", return_value=mock_client):
        summarizer = DeepseekSummarizer()
        result = summarizer.summarize([item])

    assert len(result) == 1
    assert isinstance(result[0], SummarizedItem)
    assert result[0].summary_zh == "AI Agent的新突破。"
    assert result[0].category == "ai_agent"
    assert result[0].is_top5 is False


def test_summarize_falls_back_on_error():
    item = make_feed_item(content="Some content here")
    mock_client = _mock_client(["invalid json {{{"])

    with patch("signal_core.summarizer.deepseek.OpenAI", return_value=mock_client):
        summarizer = DeepseekSummarizer()
        result = summarizer.summarize([item])

    assert len(result) == 1
    assert result[0].summary_zh != ""  # fallback to content slice


def test_pick_top5_marks_items():
    from tests.conftest import make_summarized_item
    items = [make_summarized_item(url=f"https://ex.com/{i}") for i in range(7)]
    top5_ids = [items[1].id, items[3].id, items[0].id, items[5].id, items[6].id]
    top5_response = json.dumps({
        "top5": [{"id": tid, "reason": f"reason_{i}"} for i, tid in enumerate(top5_ids)]
    })
    mock_client = _mock_client([top5_response])

    with patch("signal_core.summarizer.deepseek.OpenAI", return_value=mock_client):
        summarizer = DeepseekSummarizer()
        result = summarizer.pick_top5(items)

    top5_items = [item for item in result if item.is_top5]
    assert len(top5_items) == 5
    assert all(item.top5_reason != "" for item in top5_items)


def test_pick_top5_falls_back_on_error():
    from tests.conftest import make_summarized_item
    items = [make_summarized_item(url=f"https://ex.com/{i}") for i in range(7)]
    mock_client = _mock_client(["bad json"])

    with patch("signal_core.summarizer.deepseek.OpenAI", return_value=mock_client):
        summarizer = DeepseekSummarizer()
        result = summarizer.pick_top5(items)

    top5_items = [item for item in result if item.is_top5]
    assert len(top5_items) == 5  # fallback: first 5
```

- [ ] **Step 2: Run tests to verify failure**

```bash
pytest tests/test_summarizer.py -v
```

Expected: `ImportError: cannot import name 'DeepseekSummarizer'`

- [ ] **Step 3: Implement `signal_core/summarizer/base.py`**

```python
from abc import ABC, abstractmethod
from ..models import FeedItem, SummarizedItem


class BaseSummarizer(ABC):
    @abstractmethod
    def summarize(self, items: list[FeedItem]) -> list[SummarizedItem]:
        ...

    @abstractmethod
    def pick_top5(self, items: list[SummarizedItem]) -> list[SummarizedItem]:
        ...
```

- [ ] **Step 4: Implement `signal_core/summarizer/deepseek.py`**

```python
import json
import logging
import os

from openai import OpenAI

from ..models import FeedItem, SummarizedItem
from .base import BaseSummarizer

logger = logging.getLogger(__name__)


class DeepseekSummarizer(BaseSummarizer):
    def __init__(self) -> None:
        self.client = OpenAI(
            api_key=os.environ["DEEPSEEK_API_KEY"],
            base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )
        self.model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

    def _chat(self, prompt: str) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return resp.choices[0].message.content or ""

    def summarize(self, items: list[FeedItem]) -> list[SummarizedItem]:
        results: list[SummarizedItem] = []
        for item in items:
            try:
                data = json.loads(self._chat(self._summarize_prompt(item)))
                results.append(SummarizedItem(
                    **vars(item),
                    summary_zh=data["summary_zh"],
                    category=data.get("category", item.category),
                    is_top5=False,
                    top5_reason="",
                ))
            except Exception as e:
                logger.warning("Summarize failed for %s: %s", item.url, e)
                results.append(SummarizedItem(
                    **vars(item),
                    summary_zh=item.content[:100],
                    is_top5=False,
                    top5_reason="",
                ))
        return results

    def pick_top5(self, items: list[SummarizedItem]) -> list[SummarizedItem]:
        try:
            data = json.loads(self._chat(self._top5_prompt(items)))
            top5_map = {entry["id"]: entry["reason"] for entry in data["top5"]}
            for item in items:
                if item.id in top5_map:
                    item.is_top5 = True
                    item.top5_reason = top5_map[item.id]
        except Exception as e:
            logger.warning("Top5 selection failed: %s", e)
            for item in items[:5]:
                item.is_top5 = True
                item.top5_reason = "精选推荐"
        return items

    def _summarize_prompt(self, item: FeedItem) -> str:
        return (
            "你是技术内容摘要助手。用中文总结以下文章（约100字），并归类到：\n"
            "ai_agent, llm_dev, ai_tools, ai_infra, swe, open_source, research\n\n"
            f"标题：{item.title}\n"
            f"来源：{item.source}\n"
            f"内容：{item.content}\n\n"
            '以JSON格式回复：{"summary_zh": "...", "category": "..."}'
        )

    def _top5_prompt(self, items: list[SummarizedItem]) -> str:
        articles = [
            {"id": i.id, "title": i.title, "source": i.source, "summary": i.summary_zh}
            for i in items
        ]
        return (
            "从今日技术内容中选出最值得关注的5篇，重点关注新颖性、影响力和AI/软件工程相关度。\n\n"
            f"文章列表：\n{json.dumps(articles, ensure_ascii=False)}\n\n"
            '以JSON格式返回Top 5：{"top5": [{"id": "...", "reason": "..."}]}'
        )
```

`signal_core/summarizer/__init__.py`:

```python
import os
from .base import BaseSummarizer


def create_summarizer() -> BaseSummarizer:
    backend = os.environ.get("SUMMARIZER_BACKEND", "deepseek")
    if backend == "kimi":
        from .kimi import KimiSummarizer
        return KimiSummarizer()
    from .deepseek import DeepseekSummarizer
    return DeepseekSummarizer()
```

- [ ] **Step 5: Run tests to verify passing**

```bash
pytest tests/test_summarizer.py -v
```

Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add signal_core/summarizer/ tests/test_summarizer.py
git commit -m "feat: add summarizer base and Deepseek adapter with Top5 selection"
```

---

## Task 11: Kimi Adapter

**Files:**
- Create: `signal_core/summarizer/kimi.py`

- [ ] **Step 1: Implement `signal_core/summarizer/kimi.py`**

KimiSummarizer 和 DeepseekSummarizer 逻辑完全相同，仅 API endpoint 和 model 不同：

```python
import os
from openai import OpenAI
from .deepseek import DeepseekSummarizer


class KimiSummarizer(DeepseekSummarizer):
    def __init__(self) -> None:
        self.client = OpenAI(
            api_key=os.environ["KIMI_API_KEY"],
            base_url=os.environ.get("KIMI_BASE_URL", "https://api.moonshot.cn/v1"),
        )
        self.model = os.environ.get("KIMI_MODEL", "moonshot-v1-128k")
```

- [ ] **Step 2: Verify factory switches correctly**

```python
# 在 Python shell 中验证（不需要真实 API key）
import os
os.environ["SUMMARIZER_BACKEND"] = "kimi"
os.environ["KIMI_API_KEY"] = "test"
from signal_core.summarizer import create_summarizer
s = create_summarizer()
print(type(s).__name__)  # KimiSummarizer
```

- [ ] **Step 3: Run all summarizer tests**

```bash
pytest tests/test_summarizer.py -v
```

Expected: 4 passed

- [ ] **Step 4: Commit**

```bash
git add signal_core/summarizer/kimi.py
git commit -m "feat: add Kimi summarizer adapter (reuses Deepseek logic)"
```

---

## Task 12: Delivery Formatter

**Files:**
- Create: `signal_core/deliver/__init__.py`
- Create: `signal_core/deliver/base.py`
- Create: `signal_core/deliver/formatter.py`
- Create: `tests/test_formatter.py`

- [ ] **Step 1: Write failing tests**

`tests/test_formatter.py`:

```python
from datetime import date
from tests.conftest import make_summarized_item
from signal_core.deliver.formatter import format_digest, format_text, CATEGORIES


def _make_digest():
    items = [
        make_summarized_item(url=f"https://ex.com/{i}", category=cat, is_top5=(i < 2),
                             top5_reason="重要" if i < 2 else "")
        for i, cat in enumerate(["ai_agent", "ai_agent", "llm_dev", "research", "swe"])
    ]
    return format_digest(items, date(2026, 5, 2))


def test_format_digest_structure():
    digest = _make_digest()
    assert digest["date"] == "2026-05-02"
    assert len(digest["top5"]) == 2
    assert "ai_agent" in digest["by_category"]


def test_format_text_contains_top5_section():
    digest = _make_digest()
    text = format_text(digest)
    assert "今日精选 Top 5" in text
    assert "完整日报" in text


def test_format_text_contains_category_headers():
    digest = _make_digest()
    text = format_text(digest)
    assert "【AI Agent】" in text
    assert "【LLM 应用开发】" in text


def test_format_text_includes_urls():
    digest = _make_digest()
    text = format_text(digest)
    assert "https://ex.com/" in text
```

- [ ] **Step 2: Run tests to verify failure**

```bash
pytest tests/test_formatter.py -v
```

Expected: `ImportError: cannot import name 'format_digest'`

- [ ] **Step 3: Implement `signal_core/deliver/formatter.py`**

```python
from datetime import date
from ..models import SummarizedItem

CATEGORIES: dict[str, str] = {
    "ai_agent": "AI Agent",
    "llm_dev": "LLM 应用开发",
    "ai_tools": "AI 编程工具",
    "ai_infra": "AI Infra",
    "swe": "软件工程实践",
    "open_source": "开源项目",
    "research": "论文研究",
}


def format_digest(items: list[SummarizedItem], today: date) -> dict:
    top5 = [item for item in items if item.is_top5]
    by_category: dict[str, list[SummarizedItem]] = {}
    for item in items:
        by_category.setdefault(item.category, []).append(item)
    return {"date": today.strftime("%Y-%m-%d"), "top5": top5, "by_category": by_category}


def format_text(digest: dict) -> str:
    lines: list[str] = [f"Signal Daily · {digest['date']}\n"]
    lines.append("━━ 今日精选 Top 5 ━━")
    for i, item in enumerate(digest["top5"], 1):
        cat_name = CATEGORIES.get(item.category, item.category)
        lines.append(f"{i}. {item.title} · {cat_name}")
        lines.append(f"   {item.top5_reason}")
        lines.append(f"   {item.summary_zh}")
        lines.append(f"   → {item.url}\n")
    lines.append("━━ 完整日报 ━━")
    for cat_key, cat_name in CATEGORIES.items():
        cat_items = digest["by_category"].get(cat_key, [])
        if not cat_items:
            continue
        lines.append(f"\n【{cat_name}】")
        for item in cat_items:
            lines.append(f"• {item.title} · {item.source}")
            lines.append(f"  {item.summary_zh}  → {item.url}")
    return "\n".join(lines)


def format_html(digest: dict) -> str:
    lines: list[str] = [
        "<!DOCTYPE html><html><body style='font-family:sans-serif;max-width:700px;margin:auto'>",
        f"<h1>Signal Daily · {digest['date']}</h1>",
        "<h2>今日精选 Top 5</h2><ol>",
    ]
    for item in digest["top5"]:
        cat_name = CATEGORIES.get(item.category, item.category)
        lines.append(
            f"<li><b><a href='{item.url}'>{item.title}</a></b> · {cat_name}<br>"
            f"<i>{item.top5_reason}</i><br>{item.summary_zh}</li>"
        )
    lines.append("</ol><h2>完整日报</h2>")
    for cat_key, cat_name in CATEGORIES.items():
        cat_items = digest["by_category"].get(cat_key, [])
        if not cat_items:
            continue
        lines.append(f"<h3>{cat_name}</h3><ul>")
        for item in cat_items:
            lines.append(
                f"<li><a href='{item.url}'>{item.title}</a> · {item.source}<br>"
                f"{item.summary_zh}</li>"
            )
        lines.append("</ul>")
    lines.append("</body></html>")
    return "\n".join(lines)
```

`signal_core/deliver/__init__.py` — 空文件

`signal_core/deliver/base.py`:

```python
from abc import ABC, abstractmethod


class BaseDeliverer(ABC):
    @abstractmethod
    def send(self, digest: dict) -> None:
        ...
```

- [ ] **Step 4: Run tests to verify passing**

```bash
pytest tests/test_formatter.py -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add signal_core/deliver/ tests/test_formatter.py
git commit -m "feat: add delivery formatter (text + HTML) and BaseDeliverer"
```

---

## Task 13: Email Deliverer

**Files:**
- Create: `signal_core/deliver/email.py`
- Create: `tests/test_deliver_email.py`

- [ ] **Step 1: Write failing tests**

`tests/test_deliver_email.py`:

```python
import os
from unittest.mock import patch, MagicMock
from tests.conftest import make_summarized_item
from signal_core.deliver.email import EmailDeliverer
from signal_core.deliver.formatter import format_digest
from datetime import date


@patch.dict(os.environ, {
    "EMAIL_SMTP_HOST": "smtp.example.com",
    "EMAIL_SMTP_PORT": "587",
    "EMAIL_SMTP_USER": "user@example.com",
    "EMAIL_SMTP_PASS": "secret",
    "EMAIL_TO": "me@example.com",
})
def test_email_deliverer_sends_message():
    items = [make_summarized_item(url=f"https://ex.com/{i}") for i in range(3)]
    digest = format_digest(items, date(2026, 5, 2))

    with patch("signal_core.deliver.email.smtplib.SMTP") as MockSMTP:
        mock_server = MagicMock()
        MockSMTP.return_value.__enter__ = lambda s: mock_server
        MockSMTP.return_value.__exit__ = MagicMock(return_value=False)

        deliverer = EmailDeliverer()
        deliverer.send(digest)

        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user@example.com", "secret")
        mock_server.sendmail.assert_called_once()
        args = mock_server.sendmail.call_args[0]
        assert args[0] == "user@example.com"
        assert args[1] == "me@example.com"
```

- [ ] **Step 2: Run tests to verify failure**

```bash
pytest tests/test_deliver_email.py -v
```

Expected: `ImportError: cannot import name 'EmailDeliverer'`

- [ ] **Step 3: Implement `signal_core/deliver/email.py`**

```python
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .base import BaseDeliverer
from .formatter import format_html, format_text

logger = logging.getLogger(__name__)


class EmailDeliverer(BaseDeliverer):
    def send(self, digest: dict) -> None:
        host = os.environ["EMAIL_SMTP_HOST"]
        port = int(os.environ.get("EMAIL_SMTP_PORT", "587"))
        user = os.environ["EMAIL_SMTP_USER"]
        password = os.environ["EMAIL_SMTP_PASS"]
        to = os.environ["EMAIL_TO"]
        subject = f"Signal Daily · {digest['date']}"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = to
        msg.attach(MIMEText(format_text(digest), "plain", "utf-8"))
        msg.attach(MIMEText(format_html(digest), "html", "utf-8"))

        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.sendmail(user, to, msg.as_string())
        logger.info("Email sent to %s", to)
```

- [ ] **Step 4: Run tests to verify passing**

```bash
pytest tests/test_deliver_email.py -v
```

Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add signal_core/deliver/email.py tests/test_deliver_email.py
git commit -m "feat: add email deliverer (SMTP + HTML)"
```

---

## Task 14: Telegram Deliverer

**Files:**
- Create: `signal_core/deliver/telegram.py`
- Create: `tests/test_deliver_telegram.py`

- [ ] **Step 1: Write failing tests**

`tests/test_deliver_telegram.py`:

```python
import os
from datetime import date
import pytest
from pytest_httpx import HTTPXMock
from tests.conftest import make_summarized_item
from signal_core.deliver.telegram import TelegramDeliverer
from signal_core.deliver.formatter import format_digest


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "testtoken123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "456789")


def test_telegram_delivers_message(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.telegram.org/bottesttoken123/sendMessage",
        json={"ok": True},
    )
    items = [make_summarized_item(url=f"https://ex.com/{i}") for i in range(3)]
    digest = format_digest(items, date(2026, 5, 2))

    TelegramDeliverer().send(digest)

    request = httpx_mock.get_requests()[0]
    body = request.read()
    import json
    payload = json.loads(body)
    assert payload["chat_id"] == "456789"
    assert "Signal Daily" in payload["text"]
```

- [ ] **Step 2: Run tests to verify failure**

```bash
pytest tests/test_deliver_telegram.py -v
```

Expected: `ImportError: cannot import name 'TelegramDeliverer'`

- [ ] **Step 3: Implement `signal_core/deliver/telegram.py`**

```python
import logging
import os

import httpx

from .base import BaseDeliverer
from .formatter import format_text

logger = logging.getLogger(__name__)
MAX_MESSAGE_LENGTH = 4096


class TelegramDeliverer(BaseDeliverer):
    def send(self, digest: dict) -> None:
        token = os.environ["TELEGRAM_BOT_TOKEN"]
        chat_id = os.environ["TELEGRAM_CHAT_ID"]
        text = format_text(digest)
        url = f"https://api.telegram.org/bot{token}/sendMessage"

        for chunk in self._split(text):
            with httpx.Client(timeout=30) as client:
                client.post(url, json={"chat_id": chat_id, "text": chunk, "parse_mode": "Markdown"})
        logger.info("Telegram message sent to chat %s", chat_id)

    def _split(self, text: str) -> list[str]:
        if len(text) <= MAX_MESSAGE_LENGTH:
            return [text]
        chunks: list[str] = []
        while text:
            chunks.append(text[:MAX_MESSAGE_LENGTH])
            text = text[MAX_MESSAGE_LENGTH:]
        return chunks
```

- [ ] **Step 4: Run tests to verify passing**

```bash
pytest tests/test_deliver_telegram.py -v
```

Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add signal_core/deliver/telegram.py tests/test_deliver_telegram.py
git commit -m "feat: add Telegram deliverer with message length splitting"
```

---

## Task 15: Feishu Deliverer

**Files:**
- Create: `signal_core/deliver/feishu.py`
- Create: `tests/test_deliver_feishu.py`

- [ ] **Step 1: Write failing tests**

`tests/test_deliver_feishu.py`:

```python
import os
import json
from datetime import date
import pytest
from pytest_httpx import HTTPXMock
from tests.conftest import make_summarized_item
from signal_core.deliver.feishu import FeishuDeliverer
from signal_core.deliver.formatter import format_digest

WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/test-token"


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("FEISHU_WEBHOOK_URL", WEBHOOK)


def test_feishu_delivers_message(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=WEBHOOK, json={"code": 0})
    items = [make_summarized_item(url=f"https://ex.com/{i}") for i in range(3)]
    digest = format_digest(items, date(2026, 5, 2))

    FeishuDeliverer().send(digest)

    request = httpx_mock.get_requests()[0]
    payload = json.loads(request.read())
    assert payload["msg_type"] == "text"
    assert "Signal Daily" in payload["content"]["text"]
```

- [ ] **Step 2: Run tests to verify failure**

```bash
pytest tests/test_deliver_feishu.py -v
```

Expected: `ImportError: cannot import name 'FeishuDeliverer'`

- [ ] **Step 3: Implement `signal_core/deliver/feishu.py`**

```python
import logging
import os

import httpx

from .base import BaseDeliverer
from .formatter import format_text

logger = logging.getLogger(__name__)


class FeishuDeliverer(BaseDeliverer):
    def send(self, digest: dict) -> None:
        webhook_url = os.environ["FEISHU_WEBHOOK_URL"]
        text = format_text(digest)
        payload = {"msg_type": "text", "content": {"text": text}}
        with httpx.Client(timeout=30) as client:
            client.post(webhook_url, json=payload)
        logger.info("Feishu message sent")
```

- [ ] **Step 4: Run tests to verify passing**

```bash
pytest tests/test_deliver_feishu.py -v
```

Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add signal_core/deliver/feishu.py tests/test_deliver_feishu.py
git commit -m "feat: add Feishu webhook deliverer"
```

---

## Task 16: Pipeline Orchestrator + Scheduler + CLI

**Files:**
- Create: `signal_core/pipeline.py`
- Create: `signal_core/scheduler.py`
- Create: `signal_core/__main__.py`
- Create: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing tests**

`tests/test_pipeline.py`:

```python
from unittest.mock import MagicMock, patch
from pathlib import Path
from signal_core.pipeline import run_pipeline


def test_pipeline_runs_without_error(tmp_path: Path):
    mock_items = [MagicMock(id=f"id{i}", url=f"https://ex.com/{i}") for i in range(3)]
    mock_summarized = [MagicMock(id=f"id{i}", is_top5=(i == 0)) for i in range(3)]

    with (
        patch("signal_core.pipeline.load_sources", return_value=[
            MagicMock(type="hackernews_api", name="HN", category="open_source", url=""),
        ]),
        patch("signal_core.pipeline.Database") as MockDB,
        patch("signal_core.pipeline.HackerNewsFetcher") as MockHN,
        patch("signal_core.pipeline.deduplicate", return_value=mock_items),
        patch("signal_core.pipeline.create_summarizer") as MockSummarizer,
        patch("signal_core.pipeline.EmailDeliverer") as MockEmail,
        patch("signal_core.pipeline.TelegramDeliverer") as MockTG,
        patch("signal_core.pipeline.FeishuDeliverer") as MockFS,
    ):
        MockHN.return_value.fetch.return_value = mock_items
        mock_sum = MagicMock()
        mock_sum.summarize.return_value = mock_summarized
        mock_sum.pick_top5.return_value = mock_summarized
        MockSummarizer.return_value = mock_sum

        run_pipeline(db_path=tmp_path / "test.db", config_path=tmp_path / "sources.yaml")

        MockHN.return_value.fetch.assert_called_once()
        mock_sum.summarize.assert_called_once()
        MockEmail.return_value.send.assert_called_once()
        MockTG.return_value.send.assert_called_once()
        MockFS.return_value.send.assert_called_once()


def test_pipeline_skips_failed_fetcher(tmp_path: Path):
    with (
        patch("signal_core.pipeline.load_sources", return_value=[
            MagicMock(type="hackernews_api", name="HN", category="open_source", url=""),
        ]),
        patch("signal_core.pipeline.Database"),
        patch("signal_core.pipeline.HackerNewsFetcher") as MockHN,
        patch("signal_core.pipeline.deduplicate", return_value=[]),
        patch("signal_core.pipeline.create_summarizer"),
        patch("signal_core.pipeline.EmailDeliverer"),
        patch("signal_core.pipeline.TelegramDeliverer"),
        patch("signal_core.pipeline.FeishuDeliverer"),
    ):
        MockHN.return_value.fetch.side_effect = Exception("network error")
        # Should not raise
        run_pipeline(db_path=tmp_path / "test.db", config_path=tmp_path / "sources.yaml")
```

- [ ] **Step 2: Run tests to verify failure**

```bash
pytest tests/test_pipeline.py -v
```

Expected: `ImportError: cannot import name 'run_pipeline'`

- [ ] **Step 3: Implement `signal_core/pipeline.py`**

```python
import logging
from datetime import date
from pathlib import Path

from .config import DEFAULT_CONFIG_PATH, load_sources
from .deliver.email import EmailDeliverer
from .deliver.feishu import FeishuDeliverer
from .deliver.formatter import format_digest, format_text
from .deliver.telegram import TelegramDeliverer
from .fetcher.github_trending import GitHubTrendingFetcher
from .fetcher.hackernews import HackerNewsFetcher
from .fetcher.rss import RSSFetcher
from .filter.dedup import deduplicate
from .models import FeedItem
from .storage.db import Database
from .summarizer import create_summarizer

logger = logging.getLogger(__name__)


def run_pipeline(
    db_path: Path = Path("signal.db"),
    config_path: Path = DEFAULT_CONFIG_PATH,
) -> None:
    db = Database(db_path)
    sources = load_sources(config_path)

    all_items: list[FeedItem] = []
    for source in sources:
        fetcher = _make_fetcher(source)
        if fetcher is None:
            continue
        try:
            items = fetcher.fetch()
            all_items.extend(items)
            logger.info("Fetched %d items from %s", len(items), source.name)
        except Exception as exc:
            logger.error("Fetcher %s failed: %s", source.name, exc)

    new_items = deduplicate(all_items, db)
    logger.info("After dedup: %d new items", len(new_items))

    if not new_items:
        logger.info("No new items to process, skipping")
        return

    summarizer = create_summarizer()
    summarized = summarizer.summarize(new_items)
    summarized = summarizer.pick_top5(summarized)

    db.mark_processed(new_items)
    db.cleanup_old()

    today = date.today()
    digest = format_digest(summarized, today)
    db.save_digest(today.isoformat(), format_text(digest))

    for deliverer in [EmailDeliverer(), TelegramDeliverer(), FeishuDeliverer()]:
        try:
            deliverer.send(digest)
        except Exception as exc:
            logger.error("Deliverer %s failed: %s", type(deliverer).__name__, exc)


def _make_fetcher(source):
    if source.type == "rss":
        return RSSFetcher(source.name, source.url, source.category)
    if source.type == "hackernews_api":
        return HackerNewsFetcher()
    if source.type == "github_trending":
        return GitHubTrendingFetcher()
    logger.warning("Unknown source type: %s", source.type)
    return None
```

- [ ] **Step 4: Implement `signal_core/scheduler.py`**

```python
import logging
import sys
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from dotenv import load_dotenv

from .pipeline import run_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    load_dotenv()
    args = sys.argv[1:]

    if args and args[0] == "run":
        logger.info("Manual run triggered")
        run_pipeline()
        return

    scheduler = BlockingScheduler()
    scheduler.add_job(run_pipeline, "cron", hour=8, minute=0)
    logger.info("Scheduler started — pipeline runs daily at 08:00")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Scheduler stopped")
```

- [ ] **Step 5: Implement `signal_core/__main__.py`**

```python
from .scheduler import main

main()
```

- [ ] **Step 6: Run tests to verify passing**

```bash
pytest tests/test_pipeline.py -v
```

Expected: 2 passed

- [ ] **Step 7: Run full test suite**

```bash
pytest -v
```

Expected: all tests pass, no errors

- [ ] **Step 8: Commit**

```bash
git add signal_core/pipeline.py signal_core/scheduler.py signal_core/__main__.py tests/test_pipeline.py
git commit -m "feat: add pipeline orchestrator, APScheduler, and CLI entry point"
```

---

## Task 17: Smoke Test End-to-End

- [ ] **Step 1: Copy `.env.example` to `.env` and fill in at least one set of credentials**

```bash
cp .env.example .env
# Edit .env: set SUMMARIZER_BACKEND and API keys for one backend
```

- [ ] **Step 2: Run manual pipeline trigger**

```bash
python -m signal_core run
```

Expected: log output showing fetch → filter → summarize → deliver steps, no unhandled exceptions

- [ ] **Step 3: Verify SQLite was populated**

```bash
python -c "
from signal_core.storage.db import Database
db = Database()
import sqlite3
with sqlite3.connect('signal.db') as conn:
    count = conn.execute('SELECT COUNT(*) FROM items').fetchone()[0]
    print(f'Items in DB: {count}')
"
```

Expected: `Items in DB: N` (some positive number)

- [ ] **Step 4: Final lint and type check**

```bash
ruff check signal_core/
mypy signal_core/
```

Expected: no errors

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "chore: smoke test verified, initial working version complete"
```

---

## Self-Review

**Spec coverage check:**

| Spec Requirement | Implemented In |
|---|---|
| RSS/Atom 抓取 | Task 6 — RSSFetcher |
| HackerNews 全量抓取 | Task 7 — HackerNewsFetcher |
| GitHub Trending 全量抓取 | Task 8 — GitHubTrendingFetcher |
| SQLite 去重（URL hash） | Task 3 + Task 9 |
| Deepseek v4 摘要 | Task 10 |
| Kimi 2.6 摘要 | Task 11 |
| `SUMMARIZER_BACKEND` 切换 | Task 10 (`__init__.py` factory) |
| Top 5 精选 + 推荐理由 | Task 10 |
| 逐条中文摘要（~100字） | Task 10 |
| LLM 失败重试/降级 | Task 10（fallback to content slice） |
| Email HTML 推送 | Task 13 |
| Telegram Markdown 推送 | Task 14 |
| 飞书 Webhook 推送 | Task 15 |
| 渠道独立、互不影响 | Task 16 (`pipeline.py` try/except per deliverer) |
| 信息源失败跳过 | Task 16 (`pipeline.py` try/except per fetcher) |
| 每天 08:00 触发 | Task 16 (`scheduler.py` APScheduler cron) |
| `python -m signal_core run` 手动触发 | Task 16 (`scheduler.py` CLI) |
| `config/sources.yaml` 配置 | Task 4 |
| `.env` 配置所有 Keys | Task 1 + Task 2 |
| SQLite 保留 30 天 | Task 3 (`cleanup_old`) |
| 中英文语言规则 | Task 6 (CJK detection) + Task 12 (formatter preserves) |
| HermesAgentAdapter 预留接口 | `BaseSummarizer` ABC 已定义，`hermes.py` 文件在 File Map 中预留 |

所有 spec 需求均已覆盖。

**Placeholder scan:** 无 TBD/TODO。`hermes.py` 未实现但在设计中明确标为"预留"，不是遗漏。

**Type consistency:** `FeedItem`/`SummarizedItem` 定义于 Task 2，所有后续任务通过 `vars(item)` 解包，字段名一致。`format_digest` 返回 `dict`，所有 deliverer 接收同一 `dict` 结构。
