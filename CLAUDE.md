# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

signal-core 是一个个人信息流优化系统，每天早 8 点自动抓取 AI 与软件行业的优质内容，通过 LLM 生成摘要和精选，推送至邮件、Telegram 和飞书。

设计文档：`docs/superpowers/specs/2026-05-02-signal-core-design.md`

## Commands

```bash
# 安装依赖
pip install -e ".[dev]"

# 手动触发完整 pipeline（调试用）
python -m signal_core run

# 启动常驻调度进程
python -m signal_core serve

# 运行测试
pytest

# 运行单个测试文件
pytest tests/test_fetcher.py

# 类型检查
mypy signal_core/

# Lint
ruff check signal_core/
```

## Architecture

四阶段流水线，每天由 APScheduler 在 08:00 触发一次完整运行：

```
[Scheduler] → [Fetcher] → [Filter] → [Summarizer] → [Deliverer]
```

- **Fetcher** (`signal_core/fetcher/`) — 从三类来源抓取原始条目：RSS/Atom、HackerNews API（全量）、GitHub Trending（全量）。信息源列表由 `config/sources.yaml` 驱动。
- **Filter** (`signal_core/filter/dedup.py`) — 基于 `sha256(url)` 对比 SQLite `items` 表去重，过滤掉已处理的条目。
- **Summarizer** (`signal_core/summarizer/`) — 调用 LLM API（Deepseek v4 或 Kimi 2.6，OpenAI 兼容接口）完成两件事：逐条生成中文摘要（~100字）+ 从当日所有条目中挑选 Top 5 精选。后端通过 `SUMMARIZER_BACKEND` 环境变量切换。`BaseSummarizer` 是抽象基类，`HermesAgentAdapter` 预留但暂不实现。
- **Deliverer** (`signal_core/deliver/`) — 三个渠道独立推送，互不影响：Email（HTML）、Telegram Bot（Markdown）、飞书 Webhook（富文本卡片）。

## Data Flow & Key Types

```python
# Fetcher 输出
@dataclass
class FeedItem:
    id: str           # sha256(url)，去重键
    title: str
    url: str
    source: str
    category: str     # ai_agent | llm_dev | ai_tools | ai_infra | swe | open_source | research
    published_at: datetime
    content: str
    language: str     # "zh" | "en"

# Summarizer 输出
@dataclass
class SummarizedItem(FeedItem):
    summary_zh: str
    is_top5: bool
    top5_reason: str  # 仅 is_top5=True 时有值
```

## Storage

SQLite `signal.db` 两张表：
- `items` — 已处理条目，保留 30 天，用于 Filter 去重
- `digests` — 每日摘要结果，用于回溯

## Information Sources

GitHub Trending 和 HackerNews **全量抓取不过滤**，分类由 LLM 在 Summarizer 阶段判断。其他源在 `config/sources.yaml` 中按 category 预分类，LLM 可覆盖。

七个 category 值：`ai_agent` / `llm_dev` / `ai_tools` / `ai_infra` / `swe` / `open_source` / `research`

## Configuration

| 文件 | 用途 |
|------|------|
| `config/sources.yaml` | 信息源列表，手动增删 |
| `.env` | 所有 API Keys 和渠道配置，从 `.env.example` 复制 |

核心环境变量：`SUMMARIZER_BACKEND`、`DEEPSEEK_API_KEY`、`KIMI_API_KEY`、`EMAIL_SMTP_*`、`EMAIL_TO`、`TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID`、`FEISHU_WEBHOOK_URL`

## Error Handling Convention

- 单个信息源抓取失败：记录日志，跳过，不中断整体流程
- LLM 调用失败：重试 3 次，仍失败则跳过摘要直接推送标题+链接
- 推送渠道失败：各渠道独立，一个失败不影响其他

## Delivery Format

推送内容分两层：Top 5 精选（附推荐理由）在前，完整日报按 category 分组在后。英文条目保留英文标题，摘要用中文；中文条目全程保留中文。
