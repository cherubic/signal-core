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
