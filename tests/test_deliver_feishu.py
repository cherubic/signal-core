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


def test_feishu_raises_on_http_error(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=WEBHOOK, status_code=500)
    items = [make_summarized_item(url=f"https://ex.com/{i}") for i in range(3)]
    digest = format_digest(items, date(2026, 5, 2))

    with pytest.raises(Exception):
        FeishuDeliverer().send(digest)
