# signal-core Design Spec
_Date: 2026-05-02_

## Overview

signal-core 是一个个人信息流优化系统，每天早 8 点自动抓取 AI 与软件行业的优质内容，通过 LLM 生成摘要和精选，推送至邮件、Telegram 和飞书。

---

## Architecture

系统采用四阶段流水线架构，每天由 APScheduler 触发一次完整运行：

```
[Scheduler]
     │
     ▼
[Fetcher]  ←── config/sources.yaml
     │  抓取原始条目
     ▼
[Filter]   ←── SQLite（去重）
     │  过滤后的新条目
     ▼
[Summarizer] ←── Deepseek v4 / Kimi 2.6 API
     │  结构化摘要 + Top 5 精选
     ▼
[Deliverer]  ──► Email (HTML)
             ──► Telegram Bot (Markdown)
             ──► 飞书 Webhook (富文本卡片)
```

### Project Structure

```
signal-core/
├── config/
│   └── sources.yaml          # 信息源配置
├── signal_core/
│   ├── fetcher/
│   │   ├── rss.py            # RSS/Atom 抓取
│   │   ├── hackernews.py     # HN API 全量抓取
│   │   └── github_trending.py# GitHub Trending 抓取
│   ├── filter/
│   │   └── dedup.py          # 基于 URL hash 去重
│   ├── summarizer/
│   │   ├── base.py           # Summarizer 抽象接口
│   │   ├── deepseek.py       # Deepseek v4 Adapter
│   │   ├── kimi.py           # Kimi 2.6 Adapter
│   │   └── hermes.py         # HermesAgent Adapter（预留）
│   ├── deliver/
│   │   ├── email.py          # SMTP 发送 HTML 邮件
│   │   ├── telegram.py       # Telegram Bot API
│   │   └── feishu.py         # 飞书 Webhook
│   ├── storage/
│   │   └── db.py             # SQLite 封装
│   └── scheduler.py          # APScheduler 入口
├── logs/                     # 运行日志
├── .env                      # API Keys（不提交 git）
├── .env.example
└── pyproject.toml
```

---

## Data Model

### FeedItem

```python
@dataclass
class FeedItem:
    id: str           # sha256(url)，用于去重
    title: str
    url: str
    source: str       # 来源名称，如 "Hugging Face Blog"
    category: str     # 七个方向之一（见下方）
    published_at: datetime
    content: str      # 原文摘要或正文片段
    language: str     # "zh" | "en"
```

### SummarizedItem

```python
@dataclass
class SummarizedItem(FeedItem):
    summary_zh: str       # 中文摘要（~100字）
    is_top5: bool         # 是否入选精选
    top5_reason: str      # 精选推荐理由（仅 is_top5=True 时有值）
```

### SQLite Tables

- `items` — 所有已处理条目，保留 30 天，用于去重
- `digests` — 每日生成的摘要结果，便于回溯

---

## Information Sources

信息按七个方向分类，GitHub Trending 和 HackerNews 全量抓取，由 LLM 在摘要阶段负责归类。

| 方向 | 英文源 | 中文源 |
|------|--------|--------|
| AI Agent | LangChain Blog, AutoGPT Blog, arXiv cs.AI | 机器之心（Agent 专栏） |
| LLM 应用开发 | OpenAI Blog, Google DeepMind Blog, Meta AI Blog, Mistral Blog, Cohere Blog, Hugging Face Blog, Anthropic Blog, Simon Willison's Blog, LlamaIndex Blog | 量子位, AI科技评论, 智谱AI博客, 月之暗面(Kimi)博客, MiniMax博客, 字节跳动技术博客(豆包), 通义千问(Qwen)博客 |
| AI 编程工具 | GitHub Trending（全量）, HackerNews（全量） | 少数派 |
| AI Infra | vLLM Blog, Ray Blog, Ollama Releases, MLflow Blog | 美团技术博客 |
| 软件工程实践 | The Pragmatic Engineer, Martin Fowler, InfoQ | 阮一峰的网络日志 |
| 开源项目 | GitHub Trending（全量）, HackerNews Show HN | 开源中国 |
| 论文研究 | arXiv cs.LG/cs.CL, Papers with Code | 机器之心（论文专栏） |

**信息源配置格式（`config/sources.yaml`）：**

```yaml
sources:
  - name: "Hugging Face Blog"
    url: "https://huggingface.co/blog/feed.xml"
    type: rss
    category: llm_dev

  - name: "GitHub Trending"
    url: "https://github.com/trending"
    type: github_trending
    category: open_source   # LLM 归类后可覆盖

  - name: "HackerNews"
    type: hackernews_api
    category: open_source   # 全量抓取，LLM 归类
```

---

## Summarizer

使用 OpenAI 兼容接口调用 Deepseek v4 或 Kimi 2.6，通过 `.env` 配置切换：

```
SUMMARIZER_BACKEND=deepseek   # 或 kimi
```

**两个任务：**
1. **逐条摘要** — 每条生成中文摘要（~100字）+ 确认/更新所属方向
2. **Top 5 精选** — 从当日所有条目中挑出最值得关注的 5 条，附推荐理由

**Summarizer 抽象接口：**

```python
class BaseSummarizer(ABC):
    def summarize(self, items: list[FeedItem]) -> list[SummarizedItem]: ...
    def pick_top5(self, items: list[SummarizedItem]) -> list[SummarizedItem]: ...
```

`HermesAgentAdapter` 预留，待 Hermes Agent 调用方式稳定后实现。

---

## Delivery Format

三个渠道内容一致，格式适配各平台：

```
🔥 Signal Daily · 2026-05-02

━━ 今日精选 Top 5 ━━
1. [Title] · AI Infra
   中文摘要内容...
   → https://...

━━ 完整日报 ━━

【AI Agent】
• [Title] · LangChain Blog
  中文摘要...  → https://...

【LLM 应用开发】
• ...
```

- **语言规则**：英文内容保留英文标题，摘要用中文；中文源直接保留中文
- **Email** — HTML 格式，带排版样式
- **Telegram** — Markdown 格式
- **飞书** — 富文本卡片（Webhook）

---

## Scheduling & Operations

- **触发时间**：每天 08:00（APScheduler）
- **手动触发**：`python -m signal_core run`
- **日志**：写入 `logs/` 目录

**错误处理策略：**
- 某信息源抓取失败 → 记录日志，跳过该源，不中断整体流程
- LLM 调用失败 → 重试 3 次，仍失败则跳过摘要，直接推送标题+链接
- 推送渠道失败 → 三个渠道独立，互不影响

---

## Configuration

| 文件 | 用途 |
|------|------|
| `config/sources.yaml` | 信息源列表，手动编辑增删 |
| `.env` | API Keys、渠道配置（不提交 git） |
| SQLite `signal.db` | 运行时数据（去重记录、历史摘要） |

**`.env` 关键字段：**
```
SUMMARIZER_BACKEND=deepseek
DEEPSEEK_API_KEY=...
KIMI_API_KEY=...
EMAIL_SMTP_HOST=...
EMAIL_SMTP_USER=...
EMAIL_SMTP_PASS=...
EMAIL_TO=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
FEISHU_WEBHOOK_URL=...
```

---

## Deployment

- **第一版**：本地运行，APScheduler 常驻进程
- **后续迁移**：只需替换环境变量注入方式，核心 pipeline 代码不变，支持迁移到 VPS 或 Serverless（如 Modal、阿里云函数计算）
