import json
import os
from datetime import date

import pytest
from pytest_httpx import HTTPXMock

from signal_core.deliver.formatter import format_digest
from signal_core.deliver.telegram import TelegramDeliverer
from tests.conftest import make_summarized_item


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
    payload = json.loads(body)
    assert payload["chat_id"] == "456789"
    assert "Signal Daily" in payload["text"]


def test_telegram_splits_long_message():
    """Messages longer than 4096 chars are split into multiple chunks."""
    deliverer = TelegramDeliverer()
    long_text = "x" * 5000
    chunks = deliverer._split(long_text)
    assert len(chunks) == 2
    assert all(len(c) <= 4096 for c in chunks)
    assert "".join(chunks) == long_text


def test_telegram_short_message_not_split():
    deliverer = TelegramDeliverer()
    short_text = "hello"
    chunks = deliverer._split(short_text)
    assert chunks == ["hello"]
