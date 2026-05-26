# Tushare 智能选股 Agent 系统 — 设计文档

## 概述

基于 Tushare 金融数据接口 + DeepSeek 大模型 + LangChain Agent 框架，构建一个自动化 A 股选股与基本面分析系统。支持定时策略执行和按需交互查询，通过 Web 仪表盘和微信/邮件推送分析结果。

## 核心需求

| 维度 | 选择 |
|------|------|
| 智能体模式 | 自动化策略驱动 + 按需自由对话 |
| 交互形式 | Web 仪表盘 + 企业微信对话 + 邮件推送 |
| 大模型 | DeepSeek API |
| 市场范围 | A 股（沪深两市） |
| 分析维度 | 基础版（PE/PB/ROE/营收增速/利润增速 + 条件筛选），架构预留扩展 |
| 后端语言 | Python |
| 智能体框架 | LangChain/LangGraph |
| 架构风格 | 模块化分层架构 |

## 架构总览

```
┌─────────────────────────────────────────────────┐
│                   用户入口                        │
│   Web仪表盘         企业微信          邮件         │
│   策略管理/报告/     定时推送/         定时推送     │
│   自由对话           自由问答                      │
└──────────┬──────────────────────────────────────┘
           │  SSE / Webhook
           ▼
┌─────────────────────────────────────────────────┐
│              Web 层 (FastAPI)                    │
│  - REST API (策略CRUD、报告查询、仪表盘数据)       │
│  - SSE 端点 (对话流式响应)                        │
│  - 模板渲染 (仪表盘、对话页面)                     │
├─────────────────────────────────────────────────┤
│             调度层 (APScheduler)                  │
│  - Cron 定时触发选股任务                          │
│  - 任务状态跟踪与失败重试                          │
│  - 与 Agent 层解耦，通过函数调用衔接               │
├─────────────────────────────────────────────────┤
│             智能体层 (LangChain)                   │
│  - Router: 意图分类 (定时策略/用户提问)            │
│  - Screening Chain: 条件解析→数据查询→筛选排序     │
│  - Fundamental Chain: 指标计算→多维评估→解读       │
│  - Query Chain: 自由问答，Agent 自主选择工具       │
│  - Report Chain: 汇总→DeepSeek润色→结构化输出      │
│  - Tools: 6个 Tushare 工具 + 指标计算工具          │
├─────────────────────────────────────────────────┤
│             数据层 (Repository)                   │
│  - SQLAlchemy ORM + SQLite/Alembic               │
│  - Tushare API 客户端封装 (限频/缓存/重试)         │
│  - LRU 内存缓存 (→ 后续可升 Redis)                │
├─────────────────────────────────────────────────┤
│             通知层                                │
│  - 邮件 SMTP 推送                                 │
│  - 企业微信机器人 (Webhook 接收 + 回复)            │
└─────────────────────────────────────────────────┘
```

## 项目文件结构

```
tushare/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI 入口，生命周期管理
│   ├── config.py                  # pydantic-settings 配置
│   │
│   ├── web/                       # Web 层
│   │   ├── __init__.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── strategies.py      # 策略 CRUD API
│   │   │   ├── reports.py         # 报告查询 API
│   │   │   ├── chat.py            # SSE 流式对话 API
│   │   │   └── dashboard.py       # 仪表盘聚合 API
│   │   ├── templates/
│   │   │   ├── dashboard.html     # 仪表盘页面
│   │   │   └── chat.html          # 对话页面
│   │   └── static/
│   │
│   ├── scheduler/                 # 调度层
│   │   ├── __init__.py
│   │   ├── engine.py              # APScheduler 生命周期管理
│   │   └── jobs.py                # 选股/分析任务定义
│   │
│   ├── agent/                     # 智能体层
│   │   ├── __init__.py
│   │   ├── router.py              # 意图分类：定时策略 vs 自由问答
│   │   ├── chains/
│   │   │   ├── __init__.py
│   │   │   ├── screening.py       # 选股链
│   │   │   ├── fundamental.py     # 基本面分析链
│   │   │   ├── query.py           # 自由问答链
│   │   │   └── report.py          # 报告生成链
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── tushare_tools.py   # Tushare → LangChain Tool 封装
│   │   │   └── calc_tools.py      # 指标计算工具
│   │   └── prompts/
│   │       ├── screening.txt
│   │       ├── fundamental.txt
│   │       ├── query.txt
│   │       └── report.txt
│   │
│   ├── data/                      # 数据层
│   │   ├── __init__.py
│   │   ├── tushare_client.py      # Tushare API 封装 (限频/重试/缓存)
│   │   ├── models.py              # SQLAlchemy 模型
│   │   ├── repository.py          # 数据访问仓库
│   │   └── cache.py               # 内存缓存层
│   │
│   └── notify/                    # 通知层
│       ├── __init__.py
│       ├── email_sender.py        # SMTP 邮件
│       └── wechat_bot.py          # 企业微信机器人
│
├── migrations/                    # Alembic 数据库迁移
├── tests/
│   ├── test_agent/
│   ├── test_data/
│   └── test_web/
├── requirements.txt
├── .env.example
└── README.md
```

## 智能体层设计

### Agent 模式

采用 **ReAct Agent + Function Calling** 模式：

- DeepSeek 作为 Reasoning Engine
- Agent 自主决定：需要调用哪些 Tool、调用顺序、如何解读结果
- 不写死查询逻辑，后续新工具只需 `@tool` 声明即可加入

### 意图路由 (router.py)

```
用户输入 → 分类
  ├── "执行选股策略A" / 定时触发 → screening chain
  ├── "分析600519的ROE和估值"     → fundamental chain
  └── "什么是PE" / 其他             → query chain (自由工具调用)
```

分类逻辑：优先匹配策略名和股票代码关键词 → 其余走自由问答。

### Tools（首批 6 个）

| Tool 函数 | 描述 | Tushare 接口 |
|-----------|------|-------------|
| `get_stock_basic` | A股股票列表（代码、名称、行业） | `stock_basic` |
| `get_financial_indicators` | 财务指标（ROE/ROA/毛利率/净利率/负债率） | `fina_indicator` |
| `get_daily_basic` | 估值快照（PE/PB/PS/总市值） | `daily_basic` |
| `get_income_statement` | 利润表核心数据（营收/净利润/增速） | `income` |
| `get_industry_list` | 行业分类列表 | 本地计算/缓存 |
| `get_trade_calendar` | 交易日历 | `trade_cal` |

所有 Tool 返回 pandas DataFrame 的 JSON 序列化结果，Agent 可读性强。

### Chain 定义

| Chain | 触发者 | 流程 |
|-------|--------|------|
| **Screening** | 定时任务 / "帮我筛选XXX" | 解析筛选条件 → Agent 调 Tools 拉数据 → 条件过滤+排序 → 输出 Top N |
| **Fundamental** | 定时任务 / 用户指定股票 | 接收股票列表 → Agent 逐只调财务/估值 Tools → 多维打分 → DeepSeek 撰写分析 |
| **Query** | 用户自由提问 | 原样交给 Agent，Agent 自主选择 Tools，不预设流程 |
| **Report** | 被 Screening + Fundamental 调用 | 汇总上游结果 → DeepSeek 润色为自然语言 → 持久化到数据库 |

## 数据层设计

### 数据库模型 (SQLAlchemy)

```python
# Strategy: 选股策略定义
#   id, name, conditions(JSON), schedule(cron), enabled, created_at

# StockPool: A股股票池
#   id, ts_code, name, industry, list_date, updated_at

# TaskRun: 策略执行记录
#   id, strategy_id(FK), status(pending/running/done/failed),
#   started_at, finished_at, error_msg

# Report: 分析报告
#   id, task_run_id(FK), type(screening/fundamental),
#   content(JSON), summary_text, created_at

# ScreeningResult: 筛选结果明细 (一条策略执行 → 多只股票)
#   id, task_run_id(FK), ts_code, rank, score, metrics(JSON)
```

### Tushare 客户端 (tushare_client.py)

封装职责：
- 统一管理 `ts.pro_api(token)` 实例
- 自动处理 Tushare 频次限制（每分钟最多调用次数），sleep + retry
- DataFrame → JSON/dict 格式统一转换
- 输入校验（股票代码格式、日期范围）

### 缓存策略

| 数据 | 缓存时长 | 原因 |
|------|---------|------|
| 股票基本信息 | 24h | 几乎不变 |
| 财务指标 | 至下一财报日 | 季度更新 |
| 日线估值 | 1h | 日频变动 |
| 行业分类 | 24h | 几乎不变 |
| 交易日历 | 1天 | 每年底更新 |

开发期使用 `functools.lru_cache`（进程内存），后续可选 Redis。

## Web 层设计

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/dashboard/summary` | 仪表盘摘要（策略数、最近报告、运行状态） |
| CRUD | `/api/strategies` | 策略管理 |
| GET | `/api/strategies/{id}/runs` | 某策略的执行历史 |
| GET | `/api/reports` | 报告列表（支持按类型/日期筛选） |
| GET | `/api/reports/{id}` | 报告详情 |
| POST | `/api/chat` | 对话接口 (SSE 流式) |

### 页面

- `GET /` → dashboard.html：卡片式仪表盘，展示策略状态、最近报告摘要
- `GET /chat` → chat.html：对话窗口，输入框 + SSE 流式显示回复

### 对话流 (SSE)

```
POST /api/chat  {"message": "帮我分析600519的ROE"}
        ↓
router.classify("帮我分析600519的ROE") → fundamental
        ↓
agent.run(chain=fundamental, input="600519")
        ↓
SSE stream: data: {"type": "tool_call", "tool": "get_financial_indicators"}
            data: {"type": "thinking", "text": "..."}
            data: {"type": "answer", "text": "贵州茅台ROE..."}
            data: {"type": "done"}
```

## 调度层设计

### APScheduler 配置

- `engine.py`：启动/关闭调度器，注册 job store（数据库持久化，防重启丢失）
- `jobs.py` 定义两个内置 Job：
  - **日频选股**：每个交易日 15:30 执行（收盘后，数据就绪）
  - **周频分析**：每周五 16:00 执行（周度基本面深度分析）

### 执行流程

```
定时触发 job
  → 查询所有 enabled 的 Strategy
  → 逐一创建 TaskRun(status=pending)
  → 调 agent.router.route(strategy)
  → Screening/Fundamental Chain 执行
  → 结果写入 ScreeningResult + Report
  → 调 notify 层推送
  → TaskRun 标记 done/failed
```

### 策略条件格式 (JSON)

```json
{
  "pe_max": 30,
  "pb_max": 5,
  "roe_min": 15,
  "revenue_growth_min": 10,
  "profit_growth_min": 10,
  "industry_exclude": ["房地产", "钢铁"],
  "top_n": 20
}
```

## 通知层设计

### 邮件推送

- 使用 `smtplib` + Jinja2 模板渲染 HTML 邮件
- 推送内容：策略名称、执行时间、Top 10 结果摘要 + 完整报告链接

### 企业微信机器人

- **推送**：通过 Webhook 发送 Markdown 消息（定时任务结果摘要）
- **接收**：配置企业微信回调 URL (`/api/wechat/callback`)，接收用户消息 → 转发给 Agent → 异步返回结果
- 企业微信有 5 秒超时限制，收到消息后先回 ACK，分析完成后再主动推结果

## 技术栈

| 层 | 技术 | 说明 |
|----|------|------|
| Web 框架 | FastAPI + Jinja2 | 异步 HTTP + SSE 支持 |
| 智能体 | LangChain + langchain-deepseek | ReAct Agent + Tool Calling |
| 大模型 | DeepSeek (deepseek-chat) | OpenAI 兼容接口 |
| 数据源 | tushare (pro) | A 股数据 |
| ORM | SQLAlchemy + Alembic | 数据持久化 + 迁移 |
| 任务调度 | APScheduler | 内置调度，无需额外进程 |
| 前端 | HTML + HTMX + Alpine.js | 轻量级，无构建工具 |
| 缓存 | functools.lru_cache | 开发期，后续接 Redis |
| 通知 | smtplib + 企业微信 Webhook | 邮件 + 微信推送 |
| 配置 | pydantic-settings | 环境变量/.env |

## 后续扩展预留

- Agent 工具扩展：现金流分析、杜邦分析、技术面指标、新闻舆情
- 数据源扩展：备用数据源接口（akshare 等）
- 前端升级：需要时可接 React/Vue，API 已独立
- 数据库升级：SQLite → PostgreSQL，SQLAlchemy 无需改代码
- 多智能体协作：LangGraph 状态图可替换当前 ReAct Agent
- 回测模块：基于历史数据验证策略有效性
