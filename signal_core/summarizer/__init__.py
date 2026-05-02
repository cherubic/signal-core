import os
from .base import BaseSummarizer


def create_summarizer() -> BaseSummarizer:
    backend = os.environ.get("SUMMARIZER_BACKEND", "deepseek")
    if backend == "kimi":
        from .kimi import KimiSummarizer
        return KimiSummarizer()
    from .deepseek import DeepseekSummarizer
    return DeepseekSummarizer()
