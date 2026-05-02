import json
import os
from unittest.mock import MagicMock, patch
from tests.conftest import make_feed_item, make_summarized_item
from signal_core.summarizer.deepseek import DeepseekSummarizer
from signal_core.models import SummarizedItem


def _mock_client(responses: list[str]):
    mock = MagicMock()
    mock.chat.completions.create.side_effect = [
        MagicMock(choices=[MagicMock(message=MagicMock(content=r))])
        for r in responses
    ]
    return mock


@patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"})
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


@patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"})
def test_summarize_falls_back_on_error():
    item = make_feed_item(content="Some content here")
    mock_client = _mock_client(["invalid json {{{"])

    with patch("signal_core.summarizer.deepseek.OpenAI", return_value=mock_client):
        summarizer = DeepseekSummarizer()
        result = summarizer.summarize([item])

    assert len(result) == 1
    assert result[0].summary_zh != ""  # fallback to content slice


@patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"})
def test_pick_top5_marks_items():
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


@patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"})
def test_pick_top5_falls_back_on_error():
    items = [make_summarized_item(url=f"https://ex.com/{i}") for i in range(7)]
    mock_client = _mock_client(["bad json"])

    with patch("signal_core.summarizer.deepseek.OpenAI", return_value=mock_client):
        summarizer = DeepseekSummarizer()
        result = summarizer.pick_top5(items)

    top5_items = [item for item in result if item.is_top5]
    assert len(top5_items) == 5  # fallback: first 5
