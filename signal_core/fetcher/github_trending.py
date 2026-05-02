import hashlib
import logging
from datetime import datetime, timezone

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
                published_at=datetime.now(timezone.utc),
                content=desc,
                language="en",
            ))
        return items
