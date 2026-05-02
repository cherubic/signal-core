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
