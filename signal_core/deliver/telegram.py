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

        with httpx.Client(timeout=30) as client:
            for chunk in self._split(text):
                response = client.post(url, json={"chat_id": chat_id, "text": chunk})
                response.raise_for_status()
        logger.info("Telegram message sent to chat %s", chat_id)

    def _split(self, text: str) -> list[str]:
        if len(text) <= MAX_MESSAGE_LENGTH:
            return [text]
        chunks: list[str] = []
        while text:
            chunks.append(text[:MAX_MESSAGE_LENGTH])
            text = text[MAX_MESSAGE_LENGTH:]
        return chunks
