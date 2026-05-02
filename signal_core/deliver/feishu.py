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
            response = client.post(webhook_url, json=payload)
            response.raise_for_status()
        logger.info("Feishu message sent")
