from datetime import date
from ..models import SummarizedItem

CATEGORIES: dict[str, str] = {
    "ai_agent": "AI Agent",
    "llm_dev": "LLM 应用开发",
    "ai_tools": "AI 编程工具",
    "ai_infra": "AI Infra",
    "swe": "软件工程实践",
    "open_source": "开源项目",
    "research": "论文研究",
}


def format_digest(items: list[SummarizedItem], today: date) -> dict:
    top5 = [item for item in items if item.is_top5]
    by_category: dict[str, list[SummarizedItem]] = {}
    for item in items:
        by_category.setdefault(item.category, []).append(item)
    return {"date": today.strftime("%Y-%m-%d"), "top5": top5, "by_category": by_category}


def format_text(digest: dict) -> str:
    lines: list[str] = [f"Signal Daily · {digest['date']}\n"]
    lines.append("━━ 今日精选 Top 5 ━━")
    for i, item in enumerate(digest["top5"], 1):
        cat_name = CATEGORIES.get(item.category, item.category)
        lines.append(f"{i}. {item.title} · {cat_name}")
        lines.append(f"   {item.top5_reason}")
        lines.append(f"   {item.summary_zh}")
        lines.append(f"   → {item.url}\n")
    lines.append("━━ 完整日报 ━━")
    for cat_key, cat_name in CATEGORIES.items():
        cat_items = digest["by_category"].get(cat_key, [])
        if not cat_items:
            continue
        lines.append(f"\n【{cat_name}】")
        for item in cat_items:
            lines.append(f"• {item.title} · {item.source}")
            lines.append(f"  {item.summary_zh}  → {item.url}")
    return "\n".join(lines)


def format_html(digest: dict) -> str:
    lines: list[str] = [
        "<!DOCTYPE html><html><body style='font-family:sans-serif;max-width:700px;margin:auto'>",
        f"<h1>Signal Daily · {digest['date']}</h1>",
        "<h2>今日精选 Top 5</h2><ol>",
    ]
    for item in digest["top5"]:
        cat_name = CATEGORIES.get(item.category, item.category)
        lines.append(
            f"<li><b><a href='{item.url}'>{item.title}</a></b> · {cat_name}<br>"
            f"<i>{item.top5_reason}</i><br>{item.summary_zh}</li>"
        )
    lines.append("</ol><h2>完整日报</h2>")
    for cat_key, cat_name in CATEGORIES.items():
        cat_items = digest["by_category"].get(cat_key, [])
        if not cat_items:
            continue
        lines.append(f"<h3>{cat_name}</h3><ul>")
        for item in cat_items:
            lines.append(
                f"<li><a href='{item.url}'>{item.title}</a> · {item.source}<br>"
                f"{item.summary_zh}</li>"
            )
        lines.append("</ul>")
    lines.append("</body></html>")
    return "\n".join(lines)
