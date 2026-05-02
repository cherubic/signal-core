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
