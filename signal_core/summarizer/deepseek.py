import json
import logging
import os

from openai import OpenAI

from ..models import FeedItem, SummarizedItem
from .base import BaseSummarizer

logger = logging.getLogger(__name__)


class DeepseekSummarizer(BaseSummarizer):
    def __init__(self) -> None:
        self.client = OpenAI(
            api_key=os.environ["DEEPSEEK_API_KEY"],
            base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        )
        self.model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

    def _chat(self, prompt: str) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return resp.choices[0].message.content or ""

    def summarize(self, items: list[FeedItem]) -> list[SummarizedItem]:
        results: list[SummarizedItem] = []
        for item in items:
            try:
                data = json.loads(self._chat(self._summarize_prompt(item)))
                item_fields = {k: v for k, v in vars(item).items() if k != "category"}
                results.append(SummarizedItem(
                    **item_fields,
                    category=data.get("category", item.category),
                    summary_zh=data["summary_zh"],
                    is_top5=False,
                    top5_reason="",
                ))
            except Exception as e:
                logger.warning("Summarize failed for %s: %s", item.url, e)
                results.append(SummarizedItem(
                    **vars(item),
                    summary_zh=item.content[:100],
                    is_top5=False,
                    top5_reason="",
                ))
        return results

    def pick_top5(self, items: list[SummarizedItem]) -> list[SummarizedItem]:
        try:
            data = json.loads(self._chat(self._top5_prompt(items)))
            top5_map = {entry["id"]: entry["reason"] for entry in data["top5"]}
            for item in items:
                if item.id in top5_map:
                    item.is_top5 = True
                    item.top5_reason = top5_map[item.id]
        except Exception as e:
            logger.warning("Top5 selection failed: %s", e)
            for item in items[:5]:
                item.is_top5 = True
                item.top5_reason = "精选推荐"
        return items

    def _summarize_prompt(self, item: FeedItem) -> str:
        return (
            "你是技术内容摘要助手。用中文总结以下文章（约100字），并归类到：\n"
            "ai_agent, llm_dev, ai_tools, ai_infra, swe, open_source, research\n\n"
            f"标题：{item.title}\n"
            f"来源：{item.source}\n"
            f"内容：{item.content}\n\n"
            '以JSON格式回复：{"summary_zh": "...", "category": "..."}'
        )

    def _top5_prompt(self, items: list[SummarizedItem]) -> str:
        articles = [
            {"id": i.id, "title": i.title, "source": i.source, "summary": i.summary_zh}
            for i in items
        ]
        return (
            "从今日技术内容中选出最值得关注的5篇，重点关注新颖性、影响力和AI/软件工程相关度。\n\n"
            f"文章列表：\n{json.dumps(articles, ensure_ascii=False)}\n\n"
            '以JSON格式返回Top 5：{"top5": [{"id": "...", "reason": "..."}]}'
        )
