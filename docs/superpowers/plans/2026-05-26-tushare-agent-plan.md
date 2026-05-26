# Tushare 智能选股 Agent 系统 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从零构建 Tushare + DeepSeek + LangChain 智能选股系统，支持定时策略执行和按需对话查询。

**Architecture:** 模块化5层分层：Web (FastAPI) → Scheduler (APScheduler) → Agent (LangChain+DeepSeek) → Data (SQLAlchemy+Tushare) → Notify (SMTP+企微)。层间通过明确的 Python 接口耦合，每层独立可测试。

**Tech Stack:** Python 3.11+, FastAPI, LangChain, langchain-deepseek, DeepSeek API, Tushare Pro, SQLAlchemy, APScheduler, Jinja2, HTMX, Alpine.js

**设计文档:** `docs/superpowers/specs/2026-05-26-tushare-agent-design.md`

---

## Phase 1: 项目基础设施

### Task 1: 初始化项目仓库与目录结构

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `app/__init__.py`
- Create: `app/web/__init__.py`
- Create: `app/web/api/__init__.py`
- Create: `app/scheduler/__init__.py`
- Create: `app/agent/__init__.py`
- Create: `app/agent/chains/__init__.py`
- Create: `app/agent/tools/__init__.py`
- Create: `app/data/__init__.py`
- Create: `app/notify/__init__.py`

- [ ] **Step 1: 初始化 git 仓库**

```bash
cd "e:\Claude文件\tushare" && git init
```

- [ ] **Step 2: 创建 requirements.txt**

```txt
# Web
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
jinja2>=3.1.3
python-multipart>=0.0.9
sse-starlette>=2.0.0

# AI / Agent
langchain>=0.3.0
langchain-deepseek>=0.1.0
langchain-core>=0.3.0

# Data
tushare>=1.4.0
sqlalchemy>=2.0.0
alembic>=1.13.0
pandas>=2.2.0

# Scheduler
apscheduler>=3.10.0

# Config
pydantic-settings>=2.2.0

# Notify
aiosmtplib>=3.0.0

# Dev
pytest>=8.0.0
pytest-asyncio>=0.23.0
httpx>=0.27.0
```

- [ ] **Step 3: 创建 .env.example**

```env
# DeepSeek
DEEPSEEK_API_KEY=sk-your-deepseek-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# Tushare
TUSHARE_TOKEN=your-tushare-token

# Database (SQLite 默认，无需修改)
DATABASE_URL=sqlite:///./data/tushare.db

# Scheduler
SCHEDULER_DAILY_SCREEN_TIME=15:30
SCHEDULER_WEEKLY_ANALYSIS_DAY=fri
SCHEDULER_WEEKLY_ANALYSIS_TIME=16:00

# Email (可选)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your-email@example.com
SMTP_PASSWORD=your-password
SMTP_FROM=your-email@example.com

# 企微机器人 (可选)
WECHAT_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
WECHAT_TOKEN=your-wechat-token
WECHAT_ENCODING_AES_KEY=your-aes-key
```

- [ ] **Step 4: 创建 .gitignore**

```gitignore
__pycache__/
*.py[cod]
*.db
.env
.venv/
venv/
*.egg-info/
dist/
.pytest_cache/
data/
```

- [ ] **Step 5: 创建所有 __init__.py 和空目录**

```bash
mkdir -p app/web/api app/web/templates app/web/static \
  app/scheduler app/agent/chains app/agent/tools app/agent/prompts \
  app/data app/notify tests/test_agent tests/test_data tests/test_web \
  data

for dir in app app/web app/web/api app/scheduler app/agent app/agent/chains \
  app/agent/tools app/data app/notify; do
  touch "$dir/__init__.py"
done
```

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "chore: initialize project structure and dependencies"
```

---

### Task 2: 配置管理模块

**Files:**
- Create: `app/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: 编写配置模块测试**

```python
# tests/test_config.py
import os
import pytest
from app.config import Settings


class TestSettings:
    def test_defaults(self):
        """默认值：SQLite、标准调度时间"""
        settings = Settings(
            DEEPSEEK_API_KEY="sk-test",
            TUSHARE_TOKEN="test-token",
        )
        assert settings.DATABASE_URL == "sqlite:///./data/tushare.db"
        assert settings.DEEPSEEK_MODEL == "deepseek-chat"
        assert settings.DEEPSEEK_BASE_URL == "https://api.deepseek.com"
        assert settings.SCHEDULER_DAILY_SCREEN_TIME == "15:30"
        assert settings.SCHEDULER_WEEKLY_ANALYSIS_DAY == "fri"
        assert settings.SCHEDULER_WEEKLY_ANALYSIS_TIME == "16:00"

    def test_env_override(self, monkeypatch):
        """环境变量可覆盖默认值"""
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")
        monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-coder")
        settings = Settings(
            DEEPSEEK_API_KEY="sk-test",
            TUSHARE_TOKEN="test-token",
        )
        assert settings.DATABASE_URL == "postgresql://localhost/test"
        assert settings.DEEPSEEK_MODEL == "deepseek-coder"

    def test_missing_required_raises(self):
        """缺少必填项应报错"""
        with pytest.raises(Exception):
            Settings()  # 缺 DEEPSEEK_API_KEY 和 TUSHARE_TOKEN
```

- [ ] **Step 2: 运行测试验证失败**

```bash
python -m pytest tests/test_config.py -v
```

- [ ] **Step 3: 实现 Settings**

```python
# app/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # DeepSeek
    DEEPSEEK_API_KEY: str
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # Tushare
    TUSHARE_TOKEN: str

    # Database
    DATABASE_URL: str = "sqlite:///./data/tushare.db"

    # Scheduler
    SCHEDULER_DAILY_SCREEN_TIME: str = "15:30"
    SCHEDULER_WEEKLY_ANALYSIS_DAY: str = "fri"
    SCHEDULER_WEEKLY_ANALYSIS_TIME: str = "16:00"

    # Email (optional)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""

    # WeChat (optional)
    WECHAT_WEBHOOK_URL: str = ""
    WECHAT_TOKEN: str = ""
    WECHAT_ENCODING_AES_KEY: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
```

- [ ] **Step 4: 运行测试验证通过**

```bash
python -m pytest tests/test_config.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/config.py tests/test_config.py
git commit -m "feat: add pydantic-settings configuration module"
```

---

## Phase 2: 数据层

### Task 3: 数据库模型定义

**Files:**
- Create: `app/data/models.py`

- [ ] **Step 1: 定义所有 SQLAlchemy 模型**

```python
# app/data/models.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, DateTime, Integer, Float,
    ForeignKey, JSON, Enum as SAEnum, create_engine, UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker
import enum


class Base(DeclarativeBase):
    pass


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class ReportType(str, enum.Enum):
    SCREENING = "screening"
    FUNDAMENTAL = "fundamental"


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, unique=True)
    conditions = Column(JSON, nullable=False)
    schedule = Column(String(50), nullable=False, default="0 15 * * 1-5")
    enabled = Column(Integer, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    task_runs = relationship("TaskRun", back_populates="strategy", cascade="all, delete-orphan")


class TaskRun(Base):
    __tablename__ = "task_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    strategy_id = Column(String(36), ForeignKey("strategies.id"), nullable=False)
    status = Column(SAEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    finished_at = Column(DateTime, nullable=True)
    error_msg = Column(Text, nullable=True)

    strategy = relationship("Strategy", back_populates="task_runs")
    report = relationship("Report", back_populates="task_run", uselist=False, cascade="all, delete-orphan")
    screening_results = relationship("ScreeningResult", back_populates="task_run", cascade="all, delete-orphan")


class Report(Base):
    __tablename__ = "reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_run_id = Column(String(36), ForeignKey("task_runs.id"), nullable=False, unique=True)
    type = Column(SAEnum(ReportType), nullable=False)
    content = Column(JSON, nullable=False, default=dict)
    summary_text = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    task_run = relationship("TaskRun", back_populates="report")


class ScreeningResult(Base):
    __tablename__ = "screening_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_run_id = Column(String(36), ForeignKey("task_runs.id"), nullable=False)
    ts_code = Column(String(20), nullable=False)
    rank = Column(Integer, nullable=False)
    score = Column(Float, nullable=False, default=0.0)
    metrics = Column(JSON, nullable=False, default=dict)

    task_run = relationship("TaskRun", back_populates="screening_results")


class StockPool(Base):
    __tablename__ = "stock_pool"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ts_code = Column(String(20), nullable=False, unique=True)
    name = Column(String(50), nullable=False)
    industry = Column(String(50), nullable=False, default="")
    list_date = Column(String(10), nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
```

- [ ] **Step 2: Commit**

```bash
git add app/data/models.py
git commit -m "feat: add SQLAlchemy data models"
```

---

### Task 4: Tushare 客户端封装

**Files:**
- Create: `app/data/tushare_client.py`
- Test: `tests/test_data/test_tushare_client.py`

- [ ] **Step 1: 编写测试**

```python
# tests/test_data/test_tushare_client.py
import pytest
import pandas as pd
from app.data.tushare_client import TushareClient


class TestTushareClient:
    def test_init_with_token(self):
        client = TushareClient(token="test-token")
        assert client._token == "test-token"

    def test_format_ts_code_with_dot(self):
        """股票代码自动补全为 tushare 格式"""
        client = TushareClient(token="test-token")
        assert client._format_ts_code("600519") == "600519.SH"
        assert client._format_ts_code("000001.SZ") == "000001.SZ"
        assert client._format_ts_code("688001.SH") == "688001.SH"

    def test_format_ts_code_sse_mapping(self):
        """沪市代码映射：6xxx → .SH, 68xxx → .SH"""
        client = TushareClient(token="test-token")
        assert client._format_ts_code("600000") == "600000.SH"
        assert client._format_ts_code("688888") == "688888.SH"

    def test_format_ts_code_szse_mapping(self):
        """深市代码映射：0xxx → .SZ, 3xxx → .SZ"""
        client = TushareClient(token="test-token")
        assert client._format_ts_code("000001") == "000001.SZ"
        assert client._format_ts_code("300750") == "300750.SZ"

    def test_format_ts_code_already_formatted(self):
        """已有后缀的代码不做转换"""
        client = TushareClient(token="test-token")
        assert client._format_ts_code("600519.SH") == "600519.SH"

    def test_cache_key_generation(self):
        client = TushareClient(token="test-token")
        key = client._cache_key("stock_basic", exchange="SSE")
        assert "stock_basic" in key
        assert "SSE" in key
```

- [ ] **Step 2: 运行测试验证失败**

```bash
python -m pytest tests/test_data/test_tushare_client.py -v
```

- [ ] **Step 3: 实现 TushareClient**

```python
# app/data/tushare_client.py
import time
import hashlib
import json
from functools import lru_cache
from datetime import datetime, timedelta
import pandas as pd
import tushare as ts


class TushareClient:
    def __init__(self, token: str):
        self._token = token
        self._pro = None  # lazy init
        self._last_call = 0.0
        self._min_interval = 0.2  # Tushare 免费版每分钟 200 次，保守 0.2s 间隔

    @property
    def pro(self):
        if self._pro is None:
            self._pro = ts.pro_api(self._token)
        return self._pro

    def _rate_limit(self):
        elapsed = time.time() - self._last_call
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_call = time.time()

    @staticmethod
    def _format_ts_code(code: str) -> str:
        code = code.strip().upper()
        if "." in code:
            return code
        if code.startswith(("6", "68")):
            return f"{code}.SH"
        if code.startswith(("0", "3")):
            return f"{code}.SZ"
        return code

    @staticmethod
    def _cache_key(method: str, **kwargs) -> str:
        raw = f"{method}:{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _call_with_retry(self, func, max_retries: int = 3, **kwargs) -> pd.DataFrame:
        self._rate_limit()
        for attempt in range(max_retries):
            try:
                result = func(**kwargs)
                if result is not None and not result.empty:
                    return result
                return pd.DataFrame()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(1 * (attempt + 1))
        return pd.DataFrame()

    def get_stock_basic(self, exchange: str = "", list_status: str = "L") -> pd.DataFrame:
        kwargs = {"list_status": list_status}
        if exchange:
            kwargs["exchange"] = exchange
        return self._call_with_retry(self.pro.stock_basic, **kwargs)

    def get_daily_basic(
        self, ts_code: str = "", trade_date: str = "",
        start_date: str = "", end_date: str = ""
    ) -> pd.DataFrame:
        kwargs = {}
        if ts_code:
            kwargs["ts_code"] = ts_code
        if trade_date:
            kwargs["trade_date"] = trade_date
        if start_date:
            kwargs["start_date"] = start_date
        if end_date:
            kwargs["end_date"] = end_date
        return self._call_with_retry(self.pro.daily_basic, **kwargs)

    def get_fina_indicator(
        self, ts_code: str = "", period: str = "",
        start_date: str = "", end_date: str = ""
    ) -> pd.DataFrame:
        kwargs = {}
        if ts_code:
            kwargs["ts_code"] = ts_code
        if period:
            kwargs["period"] = period
        if start_date:
            kwargs["start_date"] = start_date
        if end_date:
            kwargs["end_date"] = end_date
        kwargs["fields"] = "ts_code,ann_date,end_date,roe,roa,grossprofit_margin,netprofit_margin,debt_to_assets,eps,dt_netprofit_yoy,or_yoy"
        return self._call_with_retry(self.pro.fina_indicator, **kwargs)

    def get_income(
        self, ts_code: str = "", period: str = "",
        start_date: str = "", end_date: str = ""
    ) -> pd.DataFrame:
        kwargs = {}
        if ts_code:
            kwargs["ts_code"] = ts_code
        if period:
            kwargs["period"] = period
        if start_date:
            kwargs["start_date"] = start_date
        if end_date:
            kwargs["end_date"] = end_date
        kwargs["fields"] = "ts_code,ann_date,end_date,revenue,operate_profit,total_profit,n_income,basic_eps"
        return self._call_with_retry(self.pro.income, **kwargs)

    def get_trade_cal(self, exchange: str = "", start_date: str = "", end_date: str = "") -> pd.DataFrame:
        kwargs = {"is_open": "1"}
        if exchange:
            kwargs["exchange"] = exchange
        if start_date:
            kwargs["start_date"] = start_date
        if end_date:
            kwargs["end_date"] = end_date
        return self._call_with_retry(self.pro.trade_cal, **kwargs)

    def get_latest_trade_date(self) -> str:
        today = datetime.now()
        cal = self.get_trade_cal(
            exchange="SSE",
            start_date=(today - timedelta(days=10)).strftime("%Y%m%d"),
            end_date=today.strftime("%Y%m%d"),
        )
        if not cal.empty:
            return str(cal["cal_date"].max())
        return today.strftime("%Y%m%d")
```

- [ ] **Step 4: 运行测试**

```bash
python -m pytest tests/test_data/test_tushare_client.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/data/tushare_client.py tests/test_data/test_tushare_client.py
git commit -m "feat: add Tushare API client with rate limiting and retry"
```

---

### Task 5: 缓存层

**Files:**
- Create: `app/data/cache.py`
- Test: `tests/test_data/test_cache.py`

- [ ] **Step 1: 编写测试**

```python
# tests/test_data/test_cache.py
import time
import pytest
from app.data.cache import CacheManager


class TestCacheManager:
    def test_get_set(self):
        cache = CacheManager()
        cache.set("key1", "value1", ttl_seconds=60)
        assert cache.get("key1") == "value1"

    def test_miss_returns_none(self):
        cache = CacheManager()
        assert cache.get("nonexistent") is None

    def test_ttl_expiry(self):
        cache = CacheManager()
        cache.set("key1", "value1", ttl_seconds=0.01)
        time.sleep(0.02)
        assert cache.get("key1") is None

    def test_delete(self):
        cache = CacheManager()
        cache.set("key1", "value1", ttl_seconds=60)
        cache.delete("key1")
        assert cache.get("key1") is None

    def test_clear(self):
        cache = CacheManager()
        cache.set("k1", "v1", ttl_seconds=60)
        cache.set("k2", "v2", ttl_seconds=60)
        cache.clear()
        assert cache.get("k1") is None
        assert cache.get("k2") is None

    def test_ttl_default(self):
        cache = CacheManager()
        cache.set("key1", "value1")  # no ttl = no expiry
        time.sleep(0.02)
        assert cache.get("key1") == "value1"

    def test_set_with_dict_value(self):
        cache = CacheManager()
        cache.set("key1", {"a": 1, "b": [1, 2, 3]}, ttl_seconds=60)
        assert cache.get("key1") == {"a": 1, "b": [1, 2, 3]}
```

- [ ] **Step 2: 运行测试验证失败**

```bash
python -m pytest tests/test_data/test_cache.py -v
```

- [ ] **Step 3: 实现缓存层**

```python
# app/data/cache.py
import time
from threading import Lock


class CacheManager:
    def __init__(self):
        self._store: dict[str, tuple[object, float | None]] = {}
        self._lock = Lock()

    def get(self, key: str) -> object | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if expires_at is not None and time.monotonic() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: object, ttl_seconds: float | None = None) -> None:
        expires_at = time.monotonic() + ttl_seconds if ttl_seconds is not None else None
        with self._lock:
            self._store[key] = (value, expires_at)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
```

- [ ] **Step 4: 运行测试验证通过**

```bash
python -m pytest tests/test_data/test_cache.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/data/cache.py tests/test_data/test_cache.py
git commit -m "feat: add thread-safe TTL cache manager"
```

---

### Task 6: 数据库仓库层

**Files:**
- Create: `app/data/repository.py`

- [ ] **Step 1: 实现 Repository**

```python
# app/data/repository.py
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import Session

from app.data.models import (
    Base, Strategy, TaskRun, Report, ScreeningResult, StockPool,
    TaskStatus, ReportType,
)


class Repository:
    def __init__(self, database_url: str):
        self._engine = create_engine(database_url, echo=False)
        Base.metadata.create_all(self._engine)

    def get_session(self) -> Session:
        return Session(self._engine)

    # ── Strategy ──

    def list_strategies(self, enabled_only: bool = False) -> list[Strategy]:
        with self.get_session() as s:
            q = s.query(Strategy)
            if enabled_only:
                q = q.filter(Strategy.enabled == 1)
            return q.order_by(Strategy.created_at.desc()).all()

    def get_strategy(self, strategy_id: str) -> Optional[Strategy]:
        with self.get_session() as s:
            return s.query(Strategy).filter(Strategy.id == strategy_id).first()

    def create_strategy(self, name: str, conditions: dict, schedule: str = "0 15 * * 1-5") -> Strategy:
        with self.get_session() as s:
            st = Strategy(name=name, conditions=conditions, schedule=schedule)
            s.add(st)
            s.commit()
            s.refresh(st)
            return st

    def update_strategy(self, strategy_id: str, **kwargs) -> Optional[Strategy]:
        with self.get_session() as s:
            st = s.query(Strategy).filter(Strategy.id == strategy_id).first()
            if not st:
                return None
            for k, v in kwargs.items():
                if hasattr(st, k):
                    setattr(st, k, v)
            s.commit()
            s.refresh(st)
            return st

    def delete_strategy(self, strategy_id: str) -> bool:
        with self.get_session() as s:
            st = s.query(Strategy).filter(Strategy.id == strategy_id).first()
            if not st:
                return False
            s.delete(st)
            s.commit()
            return True

    # ── TaskRun ──

    def create_task_run(self, strategy_id: str) -> TaskRun:
        with self.get_session() as s:
            tr = TaskRun(strategy_id=strategy_id, status=TaskStatus.PENDING)
            s.add(tr)
            s.commit()
            s.refresh(tr)
            return tr

    def update_task_run(self, task_run_id: str, **kwargs) -> Optional[TaskRun]:
        with self.get_session() as s:
            tr = s.query(TaskRun).filter(TaskRun.id == task_run_id).first()
            if not tr:
                return None
            for k, v in kwargs.items():
                if hasattr(tr, k):
                    setattr(tr, k, v)
            s.commit()
            s.refresh(tr)
            return tr

    def get_task_runs(self, strategy_id: str, limit: int = 20) -> list[TaskRun]:
        with self.get_session() as s:
            return (
                s.query(TaskRun)
                .filter(TaskRun.strategy_id == strategy_id)
                .order_by(desc(TaskRun.started_at))
                .limit(limit)
                .all()
            )

    # ── Report ──

    def create_report(self, task_run_id: str, report_type: ReportType, content: dict, summary_text: str) -> Report:
        with self.get_session() as s:
            r = Report(
                task_run_id=task_run_id,
                type=report_type,
                content=content,
                summary_text=summary_text,
            )
            s.add(r)
            s.commit()
            s.refresh(r)
            return r

    def list_reports(self, report_type: Optional[str] = None, limit: int = 20) -> list[Report]:
        with self.get_session() as s:
            q = s.query(Report)
            if report_type:
                q = q.filter(Report.type == report_type)
            return q.order_by(desc(Report.created_at)).limit(limit).all()

    def get_report(self, report_id: str) -> Optional[Report]:
        with self.get_session() as s:
            return s.query(Report).filter(Report.id == report_id).first()

    # ── ScreeningResult ──

    def save_screening_results(self, task_run_id: str, results: list[dict]) -> list[ScreeningResult]:
        with self.get_session() as s:
            rows = [
                ScreeningResult(
                    task_run_id=task_run_id,
                    ts_code=r["ts_code"],
                    rank=r["rank"],
                    score=r["score"],
                    metrics=r["metrics"],
                )
                for r in results
            ]
            s.add_all(rows)
            s.commit()
            return rows

    # ── StockPool ──

    def upsert_stocks(self, stocks: list[dict]) -> None:
        with self.get_session() as s:
            for stock in stocks:
                existing = s.query(StockPool).filter(StockPool.ts_code == stock["ts_code"]).first()
                if existing:
                    existing.name = stock["name"]
                    existing.industry = stock.get("industry", "")
                    existing.list_date = stock.get("list_date")
                    existing.updated_at = datetime.now(timezone.utc)
                else:
                    s.add(StockPool(
                        ts_code=stock["ts_code"],
                        name=stock["name"],
                        industry=stock.get("industry", ""),
                        list_date=stock.get("list_date"),
                    ))
            s.commit()

    def get_all_stocks(self) -> list[StockPool]:
        with self.get_session() as s:
            return s.query(StockPool).all()
```

- [ ] **Step 2: Commit**

```bash
git add app/data/repository.py
git commit -m "feat: add data repository layer with CRUD operations"
```

---

## Phase 3: 智能体层

### Task 7: LangChain Tools — Tushare 工具

**Files:**
- Create: `app/agent/tools/tushare_tools.py`

- [ ] **Step 1: 实现 Tushare LangChain Tools**

```python
# app/agent/tools/tushare_tools.py
import json
from langchain_core.tools import tool
from app.data.tushare_client import TushareClient


# 全局客户端实例，在应用启动时注入
_client: TushareClient | None = None


def set_tushare_client(client: TushareClient) -> None:
    global _client
    _client = client


def _get_client() -> TushareClient:
    if _client is None:
        raise RuntimeError("TushareClient not initialized")
    return _client


@tool
def get_stock_basic(exchange: str = "") -> str:
    """获取 A 股股票基本信息列表，包含股票代码、名称、行业、上市日期。
    参数 exchange 可选：'SSE' 上交所，'SZSE' 深交所，空字符串表示全部。"""
    client = _get_client()
    df = client.get_stock_basic(exchange=exchange)
    if df.empty:
        return json.dumps({"error": "无数据"}, ensure_ascii=False)
    subset = df[["ts_code", "name", "industry", "list_date"]].head(500).copy()
    return subset.to_json(orient="records", force_ascii=False)


@tool
def get_financial_indicators(ts_code: str, period: str = "") -> str:
    """获取指定股票的财务指标：ROE、ROA、毛利率、净利率、资产负债率、净利润同比、营收同比。
    参数 ts_code：股票代码如 '600519.SH'，period：财报期如 '20241231'。"""
    client = _get_client()
    ts_code = client._format_ts_code(ts_code)
    kwargs = {"ts_code": ts_code}
    if period:
        kwargs["period"] = period
    else:
        kwargs["start_date"] = "20230101"
    df = client.get_fina_indicator(**kwargs)
    if df.empty:
        return json.dumps({"error": f"未找到 {ts_code} 的财务数据"}, ensure_ascii=False)
    df = df.sort_values("end_date", ascending=False).head(8)
    return df.to_json(orient="records", force_ascii=False)


@tool
def get_daily_basic(ts_code: str, trade_date: str = "") -> str:
    """获取股票的日频估值数据：PE、PB、PS、总市值、流通市值、换手率。
    参数 ts_code：股票代码，trade_date：交易日期如 '20260101'，空为最新。"""
    client = _get_client()
    ts_code = client._format_ts_code(ts_code)
    if not trade_date:
        trade_date = client.get_latest_trade_date()
    df = client.get_daily_basic(ts_code=ts_code, trade_date=trade_date)
    if df.empty:
        return json.dumps({"error": f"未找到 {ts_code} 的估值数据"}, ensure_ascii=False)
    return df.head(5).to_json(orient="records", force_ascii=False)


@tool
def get_income_statement(ts_code: str, period: str = "") -> str:
    """获取利润表数据：营业收入、营业利润、净利润、基本每股收益。
    参数 ts_code：股票代码，period：报告期如 '20241231'。"""
    client = _get_client()
    ts_code = client._format_ts_code(ts_code)
    kwargs = {"ts_code": ts_code}
    if period:
        kwargs["period"] = period
    else:
        kwargs["start_date"] = "20230101"
    df = client.get_income(**kwargs)
    if df.empty:
        return json.dumps({"error": f"未找到 {ts_code} 的利润表数据"}, ensure_ascii=False)
    df = df.sort_values("end_date", ascending=False).head(8)
    return df.to_json(orient="records", force_ascii=False)


@tool
def get_industry_list() -> str:
    """获取所有 A 股行业分类列表，返回行业名称和股票数量。"""
    client = _get_client()
    df = client.get_stock_basic()
    if df.empty:
        return json.dumps({"error": "无行业数据"}, ensure_ascii=False)
    industry_counts = df.groupby("industry").size().reset_index(name="count")
    industry_counts = industry_counts.sort_values("count", ascending=False)
    return industry_counts.to_json(orient="records", force_ascii=False)


@tool
def get_trade_calendar(start_date: str, end_date: str) -> str:
    """获取交易日历，返回指定日期范围内的交易日列表。
    参数 start_date/end_date：日期格式 'YYYYMMDD'。"""
    client = _get_client()
    df = client.get_trade_cal(start_date=start_date, end_date=end_date)
    if df.empty:
        return json.dumps({"trading_days": []}, ensure_ascii=False)
    days = sorted(df["cal_date"].tolist())
    return json.dumps({"trading_days": days, "count": len(days)}, ensure_ascii=False)
```

- [ ] **Step 2: Commit**

```bash
git add app/agent/tools/tushare_tools.py
git commit -m "feat: add LangChain tools wrapping Tushare APIs"
```

---

### Task 8: Prompt 模板

**Files:**
- Create: `app/agent/prompts/screening.txt`
- Create: `app/agent/prompts/fundamental.txt`
- Create: `app/agent/prompts/query.txt`
- Create: `app/agent/prompts/report.txt`

- [ ] **Step 1: 编写 prompt 模板**

```txt
# app/agent/prompts/screening.txt
你是一位专业的 A 股量化选股分析师。你的任务是根据给定的筛选条件，使用可用的工具来筛选符合条件的股票。

请遵循以下步骤：
1. 首先获取全市场股票列表了解覆盖范围
2. 根据筛选条件，使用财务指标和估值数据工具查询数据
3. 对所有符合条件的股票按综合得分排序
4. 输出 Top N 的股票列表，包含代码、名称、行业、核心指标

筛选条件通常包括市盈率上限、市净率上限、ROE 下限、营收增速下限等。
请确保你使用了当前最新的财务数据。
```

```txt
# app/agent/prompts/fundamental.txt
你是一位资深的 A 股基本面分析师。你的任务是对给定的股票进行深度基本面分析。

请对每只股票依次：
1. 使用 get_financial_indicators 获取最新 ROE、ROA、毛利率、净利率、资产负债率、净利润同比、营收同比
2. 使用 get_daily_basic 获取当前 PE、PB、PS、总市值
3. 使用 get_income_statement 获取近几期营收和利润变化趋势
4. 综合评估该公司是否值得投资

输出格式：
- 股票代码和名称
- 核心财务指标一览
- 估值水平评价（低估/合理/高估）
- 成长性评价（加速/稳定/减速）
- 盈利能力评价
- 综合评分和一句话投资建议
```

```txt
# app/agent/prompts/query.txt
你是一位专业的 A 股投资研究助手。你可以使用以下工具来回答用户关于股票的任何问题：
- get_stock_basic：查询股票基本信息
- get_financial_indicators：查询财务指标
- get_daily_basic：查询估值数据
- get_income_statement：查询利润表
- get_industry_list：查询行业分类
- get_trade_calendar：查询交易日历

请根据用户的提问自主判断需要调用哪些工具，并以清晰、结构化的方式呈现答案。
如果用户的问题不涉及具体数据查询，请用你的专业知识直接回答。
始终用中文回复。
```

```txt
# app/agent/prompts/report.txt
你是一位金融报告撰写专家。请根据提供的选股或基本面分析原始数据，撰写一份结构化的投资研究报告。

报告应包含以下部分：
1. **概述**：本次分析的目的和范围
2. **核心发现**：3-5 个关键要点
3. **详细分析**：数据解读和趋势判断
4. **风险提示**：需要关注的风险因素
5. **总结**：综合投资建议

请使用专业但不晦涩的语言，面向有一定投资经验的读者。
```

- [ ] **Step 2: Commit**

```bash
git add app/agent/prompts/
git commit -m "feat: add agent prompt templates for all chains"
```

---

### Task 9: Agent Chains — Screening & Fundamental

**Files:**
- Create: `app/agent/chains/screening.py`
- Create: `app/agent/chains/fundamental.py`

- [ ] **Step 1: 实现选股链**

```python
# app/agent/chains/screening.py
import json
from langchain_deepseek import ChatDeepSeek
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

from app.agent.tools.tushare_tools import (
    get_stock_basic, get_financial_indicators, get_daily_basic, get_income_statement,
    get_industry_list, get_trade_calendar,
)

SCREENING_PROMPT_FILE = "app/agent/prompts/screening.txt"


def _load_prompt() -> str:
    with open(SCREENING_PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()


def build_screening_executor(llm: ChatDeepSeek) -> AgentExecutor:
    tools = [
        get_stock_basic, get_financial_indicators, get_daily_basic,
        get_income_statement, get_industry_list, get_trade_calendar,
    ]
    system_prompt = _load_prompt()
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=10)


def run_screening(executor: AgentExecutor, strategy_name: str, conditions: dict) -> dict:
    conditions_str = json.dumps(conditions, ensure_ascii=False)
    input_text = (
        f"请执行选股策略「{strategy_name}」，筛选条件如下：\n{conditions_str}\n\n"
        f"请输出排名前 {conditions.get('top_n', 20)} 的股票，格式为 JSON 数组，"
        f"每项包含 ts_code、name、industry、rank、score (0-100)、metrics (pe、pb、roe等关键值)。"
    )
    result = executor.invoke({"input": input_text})
    return {"strategy": strategy_name, "conditions": conditions, "output": result["output"]}
```

```python
# app/agent/chains/fundamental.py
import json
from langchain_deepseek import ChatDeepSeek
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

from app.agent.tools.tushare_tools import (
    get_stock_basic, get_financial_indicators, get_daily_basic, get_income_statement,
    get_industry_list, get_trade_calendar,
)

FUNDAMENTAL_PROMPT_FILE = "app/agent/prompts/fundamental.txt"


def _load_prompt() -> str:
    with open(FUNDAMENTAL_PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()


def build_fundamental_executor(llm: ChatDeepSeek) -> AgentExecutor:
    tools = [
        get_stock_basic, get_financial_indicators, get_daily_basic,
        get_income_statement, get_industry_list, get_trade_calendar,
    ]
    system_prompt = _load_prompt()
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=10)


def run_fundamental(executor: AgentExecutor, stock_codes: list[str]) -> dict:
    codes_str = ", ".join(stock_codes)
    input_text = f"请对以下股票进行基本面分析：{codes_str}。请为每只股票输出深度分析。"
    result = executor.invoke({"input": input_text})
    return {"stocks": stock_codes, "output": result["output"]}
```

- [ ] **Step 2: Commit**

```bash
git add app/agent/chains/screening.py app/agent/chains/fundamental.py
git commit -m "feat: add screening and fundamental analysis chains"
```

---

### Task 10: Agent Chains — Query & Report

**Files:**
- Create: `app/agent/chains/query.py`
- Create: `app/agent/chains/report.py`

- [ ] **Step 1: 实现自由问答链和报告链**

```python
# app/agent/chains/query.py
from typing import AsyncIterator
from langchain_deepseek import ChatDeepSeek
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

from app.agent.tools.tushare_tools import (
    get_stock_basic, get_financial_indicators, get_daily_basic, get_income_statement,
    get_industry_list, get_trade_calendar,
)

QUERY_PROMPT_FILE = "app/agent/prompts/query.txt"


def _load_prompt() -> str:
    with open(QUERY_PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()


def build_query_executor(llm: ChatDeepSeek) -> AgentExecutor:
    tools = [
        get_stock_basic, get_financial_indicators, get_daily_basic,
        get_income_statement, get_industry_list, get_trade_calendar,
    ]
    system_prompt = _load_prompt()
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=10)


async def run_query_stream(executor: AgentExecutor, message: str) -> AsyncIterator[str]:
    """流式执行自由问答，yield SSE 事件字符串"""
    # 使用 astream_events 获取中间步骤
    async for event in executor.astream_events({"input": message}, version="v2"):
        kind = event.get("event", "")
        if kind == "on_tool_start":
            tool_name = event.get("name", "unknown")
            yield f'data: {{"type": "tool_call", "tool": "{tool_name}"}}\n\n'
        elif kind == "on_tool_end":
            yield f'data: {{"type": "tool_result", "tool": "{event.get("name", "unknown")}"}}\n\n'
        elif kind == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk", None)
            if chunk and hasattr(chunk, "content") and chunk.content:
                yield f'data: {{"type": "thinking", "text": {__import__("json").dumps(chunk.content, ensure_ascii=False)}}}\n\n'

    yield 'data: {"type": "done"}\n\n'
```

```python
# app/agent/chains/report.py
import json
from langchain_deepseek import ChatDeepSeek
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

REPORT_PROMPT_FILE = "app/agent/prompts/report.txt"


def _load_prompt() -> str:
    with open(REPORT_PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()


def generate_report(llm: ChatDeepSeek, analysis_type: str, raw_data: dict) -> str:
    """将原始分析结果润色为结构化报告文本。"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", _load_prompt()),
        ("human", "分析类型：{analysis_type}\n原始数据：\n{raw_data}\n\n请撰写报告。"),
    ])
    chain = prompt | llm | StrOutputParser()
    result = chain.invoke({
        "analysis_type": analysis_type,
        "raw_data": json.dumps(raw_data, ensure_ascii=False, indent=2),
    })
    return result
```

- [ ] **Step 2: Commit**

```bash
git add app/agent/chains/query.py app/agent/chains/report.py
git commit -m "feat: add query chain with streaming and report generation chain"
```

---

### Task 11: Agent 路由器

**Files:**
- Create: `app/agent/router.py`

- [ ] **Step 1: 实现意图路由**

```python
# app/agent/router.py
import re
from dataclasses import dataclass
from langchain_deepseek import ChatDeepSeek

from app.agent.chains.screening import build_screening_executor, run_screening
from app.agent.chains.fundamental import build_fundamental_executor, run_fundamental
from app.agent.chains.query import build_query_executor, run_query_stream
from app.agent.chains.report import generate_report

STOCK_CODE_PATTERN = re.compile(r"\b(6\d{5}|0\d{5}|3\d{5})\b")
STRATEGY_KEYWORDS = [
    "筛选", "选股", "海选", "扫描", "策略", "筛", "选",
    "执行策略", "运行策略", "开始选股",
]


@dataclass
class RouteResult:
    chain: str  # "screening", "fundamental", "query"
    input_text: str
    strategy_name: str | None = None
    conditions: dict | None = None
    stock_codes: list[str] | None = None


class AgentRouter:
    def __init__(self, settings):
        self._llm = ChatDeepSeek(
            model=settings.DEEPSEEK_MODEL,
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            temperature=0.3,
        )
        self._screening_exec = build_screening_executor(self._llm)
        self._fundamental_exec = build_fundamental_executor(self._llm)
        self._query_exec = build_query_executor(self._llm)

    def classify(self, message: str) -> RouteResult:
        """分类用户输入，返回路由结果"""
        # 检查是否包含策略执行关键词
        for kw in STRATEGY_KEYWORDS:
            if kw in message:
                return RouteResult(chain="screening", input_text=message)

        # 检查是否包含股票代码
        codes = STOCK_CODE_PATTERN.findall(message)
        if codes:
            return RouteResult(chain="fundamental", input_text=message, stock_codes=list(set(codes)))

        # 默认走自由问答
        return RouteResult(chain="query", input_text=message)

    def run_screening_for_strategy(self, strategy_name: str, conditions: dict) -> dict:
        return run_screening(self._screening_exec, strategy_name, conditions)

    def run_fundamental_for_stocks(self, stock_codes: list[str]) -> dict:
        return run_fundamental(self._fundamental_exec, stock_codes)

    async def run_query_stream(self, message: str):
        async for event in run_query_stream(self._query_exec, message):
            yield event

    def generate_report(self, analysis_type: str, raw_data: dict) -> str:
        return generate_report(self._llm, analysis_type, raw_data)

    @property
    def llm(self):
        return self._llm
```

- [ ] **Step 2: Commit**

```bash
git add app/agent/router.py
git commit -m "feat: add agent router with intent classification"
```

---

## Phase 4: 调度与通知

### Task 12: 调度引擎与任务

**Files:**
- Create: `app/scheduler/engine.py`
- Create: `app/scheduler/jobs.py`

- [ ] **Step 1: 实现调度引擎**

```python
# app/scheduler/engine.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger


_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        raise RuntimeError("Scheduler not started")
    return _scheduler


def start_scheduler(database_url: str) -> AsyncIOScheduler:
    global _scheduler
    jobstore = SQLAlchemyJobStore(url=database_url)
    _scheduler = AsyncIOScheduler()
    _scheduler.add_jobstore(jobstore, "default")
    _scheduler.start()
    return _scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def add_daily_job(func, hour: int, minute: int, job_id: str) -> None:
    s = get_scheduler()
    s.add_job(
        func,
        trigger=CronTrigger(hour=hour, minute=minute, day_of_week="mon-fri"),
        id=job_id,
        replace_existing=True,
    )


def add_weekly_job(func, day_of_week: str, hour: int, minute: int, job_id: str) -> None:
    s = get_scheduler()
    s.add_job(
        func,
        trigger=CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute),
        id=job_id,
        replace_existing=True,
    )
```

```python
# app/scheduler/jobs.py
import asyncio
import logging
from datetime import datetime, timezone

from app.data.repository import Repository
from app.data.models import TaskStatus, ReportType
from app.agent.router import AgentRouter

logger = logging.getLogger(__name__)

# 这些在应用启动时注入
_repo: Repository | None = None
_router: AgentRouter | None = None


def init_jobs(repo: Repository, router: AgentRouter) -> None:
    global _repo, _router
    _repo = repo
    _router = router


async def daily_screening_job() -> None:
    """日频选股任务：对所有启用的策略执行选股"""
    if _repo is None or _router is None:
        logger.error("Jobs not initialized")
        return

    strategies = _repo.list_strategies(enabled_only=True)
    logger.info(f"日频选股开始，共 {len(strategies)} 个策略")

    for st in strategies:
        try:
            task_run = _repo.create_task_run(st.id)
            _repo.update_task_run(task_run.id, status=TaskStatus.RUNNING)

            result = _router.run_screening_for_strategy(st.name, st.conditions)

            # 解析 Agent 输出
            screening_data = result.get("output", {})
            summary = _router.generate_report("screening", screening_data)
            _repo.create_report(task_run.id, ReportType.SCREENING, screening_data, summary)

            _repo.update_task_run(task_run.id, status=TaskStatus.DONE, finished_at=datetime.now(timezone.utc))
            logger.info(f"策略「{st.name}」执行完成，报告ID: {task_run.id}")
        except Exception as e:
            logger.error(f"策略「{st.name}」执行失败: {e}")
            if _repo:
                runs = _repo.get_task_runs(st.id, limit=1)
                if runs:
                    _repo.update_task_run(runs[0].id, status=TaskStatus.FAILED, error_msg=str(e))


async def weekly_analysis_job() -> None:
    """周频分析：对股票池重点标的做深度基本面分析"""
    if _repo is None or _router is None:
        logger.error("Jobs not initialized")
        return

    stocks = _repo.get_all_stocks()
    if not stocks:
        logger.warning("股票池为空，跳过周频分析")
        return

    codes = [s.ts_code for s in stocks[:20]]  # 取前20只
    logger.info(f"周频分析开始，共 {len(codes)} 只股票")

    try:
        strategy = _repo.list_strategies(enabled_only=True)
        st_id = strategy[0].id if strategy else None
        if st_id is None:
            return
        task_run = _repo.create_task_run(st_id)
        _repo.update_task_run(task_run.id, status=TaskStatus.RUNNING)

        result = _router.run_fundamental_for_stocks(codes)
        summary = _router.generate_report("fundamental", result)
        _repo.create_report(task_run.id, ReportType.FUNDAMENTAL, result, summary)

        _repo.update_task_run(task_run.id, status=TaskStatus.DONE, finished_at=datetime.now(timezone.utc))
        logger.info("周频分析完成")
    except Exception as e:
        logger.error(f"周频分析失败: {e}")
```

- [ ] **Step 2: Commit**

```bash
git add app/scheduler/engine.py app/scheduler/jobs.py
git commit -m "feat: add APScheduler engine and daily/weekly jobs"
```

---

### Task 13: 通知层

**Files:**
- Create: `app/notify/email_sender.py`
- Create: `app/notify/wechat_bot.py`

- [ ] **Step 1: 实现邮件推送**

```python
# app/notify/email_sender.py
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

logger = logging.getLogger(__name__)


class EmailSender:
    def __init__(self, host: str, port: int, user: str, password: str, from_addr: str):
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._from = from_addr

    @property
    def enabled(self) -> bool:
        return bool(self._host and self._user)

    def send(self, to: str, subject: str, html_body: str) -> bool:
        if not self.enabled:
            logger.warning("邮件服务未配置，跳过发送")
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._from
        msg["To"] = to
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            with smtplib.SMTP(self._host, self._port, timeout=10) as server:
                server.starttls()
                server.login(self._user, self._password)
                server.sendmail(self._from, [to], msg.as_string())
            logger.info(f"邮件已发送: {subject}")
            return True
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False
```

```python
# app/notify/wechat_bot.py
import json
import logging
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


class WeChatBot:
    def __init__(self, webhook_url: str):
        self._webhook_url = webhook_url

    @property
    def enabled(self) -> bool:
        return bool(self._webhook_url)

    def send_markdown(self, content: str) -> bool:
        """通过企微 Webhook 发送 Markdown 消息"""
        if not self.enabled:
            logger.warning("企微 Webhook 未配置，跳过推送")
            return False

        payload = {
            "msgtype": "markdown",
            "markdown": {"content": content},
        }
        try:
            req = Request(
                self._webhook_url,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            urlopen(req, timeout=5)
            logger.info("企微消息已推送")
            return True
        except Exception as e:
            logger.error(f"企微推送失败: {e}")
            return False

    def send_text(self, content: str, mentioned_list: list[str] | None = None) -> bool:
        """发送文本消息，可选 @ 指定人"""
        if not self.enabled:
            return False
        payload = {
            "msgtype": "text",
            "text": {
                "content": content,
                "mentioned_list": mentioned_list or [],
            },
        }
        try:
            req = Request(
                self._webhook_url,
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            urlopen(req, timeout=5)
            return True
        except Exception as e:
            logger.error(f"企微推送失败: {e}")
            return False
```

- [ ] **Step 2: Commit**

```bash
git add app/notify/email_sender.py app/notify/wechat_bot.py
git commit -m "feat: add email and WeChat notification senders"
```

---

## Phase 5: Web 层

### Task 14: Strategy & Report REST API

**Files:**
- Create: `app/web/api/strategies.py`
- Create: `app/web/api/reports.py`

- [ ] **Step 1: 实现策略 CRUD API**

```python
# app/web/api/strategies.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.data.repository import Repository

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


class StrategyCreate(BaseModel):
    name: str
    conditions: dict
    schedule: str = "0 15 * * 1-5"


class StrategyUpdate(BaseModel):
    name: str | None = None
    conditions: dict | None = None
    schedule: str | None = None
    enabled: int | None = None


_repo: Repository | None = None


def init(repo: Repository) -> None:
    global _repo
    _repo = repo


def _get_repo() -> Repository:
    if _repo is None:
        raise RuntimeError("Repository not initialized")
    return _repo


@router.get("")
def list_strategies(enabled_only: bool = False):
    repo = _get_repo()
    strategies = repo.list_strategies(enabled_only=enabled_only)
    return [
        {
            "id": s.id, "name": s.name, "conditions": s.conditions,
            "schedule": s.schedule, "enabled": s.enabled, "created_at": str(s.created_at),
        }
        for s in strategies
    ]


@router.post("")
def create_strategy(body: StrategyCreate):
    repo = _get_repo()
    try:
        s = repo.create_strategy(body.name, body.conditions, body.schedule)
        return {"id": s.id, "name": s.name}
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("/{strategy_id}")
def get_strategy(strategy_id: str):
    repo = _get_repo()
    s = repo.get_strategy(strategy_id)
    if not s:
        raise HTTPException(404, "策略不存在")
    return {
        "id": s.id, "name": s.name, "conditions": s.conditions,
        "schedule": s.schedule, "enabled": s.enabled, "created_at": str(s.created_at),
    }


@router.put("/{strategy_id}")
def update_strategy(strategy_id: str, body: StrategyUpdate):
    repo = _get_repo()
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    s = repo.update_strategy(strategy_id, **updates)
    if not s:
        raise HTTPException(404, "策略不存在")
    return {"id": s.id, "updated": True}


@router.delete("/{strategy_id}")
def delete_strategy(strategy_id: str):
    repo = _get_repo()
    ok = repo.delete_strategy(strategy_id)
    if not ok:
        raise HTTPException(404, "策略不存在")
    return {"deleted": True}


@router.get("/{strategy_id}/runs")
def get_strategy_runs(strategy_id: str, limit: int = 20):
    repo = _get_repo()
    runs = repo.get_task_runs(strategy_id, limit=limit)
    return [
        {
            "id": r.id, "status": r.status.value, "started_at": str(r.started_at),
            "finished_at": str(r.finished_at) if r.finished_at else None,
            "error_msg": r.error_msg,
        }
        for r in runs
    ]
```

```python
# app/web/api/reports.py
from fastapi import APIRouter, HTTPException, Query

from app.data.repository import Repository

router = APIRouter(prefix="/api/reports", tags=["reports"])

_repo: Repository | None = None


def init(repo: Repository) -> None:
    global _repo
    _repo = repo


def _get_repo() -> Repository:
    if _repo is None:
        raise RuntimeError("Repository not initialized")
    return _repo


@router.get("")
def list_reports(type: str | None = Query(None), limit: int = 20):
    repo = _get_repo()
    reports = repo.list_reports(report_type=type, limit=limit)
    return [
        {
            "id": r.id, "type": r.type.value, "summary_text": r.summary_text[:200],
            "created_at": str(r.created_at), "task_run_id": r.task_run_id,
        }
        for r in reports
    ]


@router.get("/{report_id}")
def get_report(report_id: str):
    repo = _get_repo()
    r = repo.get_report(report_id)
    if not r:
        raise HTTPException(404, "报告不存在")
    return {
        "id": r.id, "type": r.type.value, "content": r.content,
        "summary_text": r.summary_text, "created_at": str(r.created_at),
    }
```

- [ ] **Step 2: Commit**

```bash
git add app/web/api/strategies.py app/web/api/reports.py
git commit -m "feat: add strategy CRUD and report query REST APIs"
```

---

### Task 15: Chat SSE API

**Files:**
- Create: `app/web/api/chat.py`

- [ ] **Step 1: 实现流式对话 API**

```python
# app/web/api/chat.py
import logging
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.agent.router import AgentRouter

router = APIRouter(prefix="/api", tags=["chat"])

logger = logging.getLogger(__name__)

_router: AgentRouter | None = None


def init(router_: AgentRouter) -> None:
    global _router
    _router = router_


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
async def chat(req: ChatRequest):
    """SSE 流式对话接口"""
    if _router is None:
        return {"error": "Agent not initialized"}

    async def event_generator():
        async for event in _router.run_query_stream(req.message):
            yield {"event": "message", "data": event.replace("data: ", "")}

    return EventSourceResponse(event_generator())
```

- [ ] **Step 2: Commit**

```bash
git add app/web/api/chat.py
git commit -m "feat: add SSE streaming chat API"
```

---

### Task 16: Dashboard API & HTML 页面

**Files:**
- Create: `app/web/api/dashboard.py`
- Create: `app/web/templates/dashboard.html`
- Create: `app/web/templates/chat.html`

- [ ] **Step 1: 实现仪表盘 API**

```python
# app/web/api/dashboard.py
from fastapi import APIRouter

from app.data.repository import Repository

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

_repo: Repository | None = None


def init(repo: Repository) -> None:
    global _repo
    _repo = repo


@router.get("/summary")
def summary():
    if _repo is None:
        return {}
    strategies = _repo.list_strategies()
    reports = _repo.list_reports(limit=5)
    return {
        "strategy_count": len(strategies),
        "enabled_count": sum(1 for s in strategies if s.enabled),
        "recent_reports": [
            {"id": r.id, "type": r.type.value, "summary": r.summary_text[:100]}
            for r in reports
        ],
    }
```

- [ ] **Step 2: 实现仪表盘 HTML 页面**

```html
<!-- app/web/templates/dashboard.html -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tushare Agent - 仪表盘</title>
    <script src="https://unpkg.com/alpinejs@3.13.5/dist/cdn.min.js" defer></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; color: #333; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: #1a1a2e; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
        .header h1 { font-size: 24px; }
        .header nav a { color: #a0a0ff; text-decoration: none; margin-left: 20px; }
        .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .card { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .card h3 { font-size: 16px; color: #666; margin-bottom: 10px; }
        .card .value { font-size: 36px; font-weight: bold; color: #1a1a2e; }
        .section { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .section h2 { font-size: 18px; margin-bottom: 15px; border-bottom: 2px solid #1a1a2e; padding-bottom: 8px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { text-align: left; padding: 10px; border-bottom: 1px solid #eee; }
        th { color: #666; font-weight: 600; font-size: 14px; }
        .btn { display: inline-block; padding: 8px 16px; background: #1a1a2e; color: white; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; font-size: 14px; }
        .btn:hover { background: #333; }
        .status { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 12px; }
        .status.active { background: #d4edda; color: #155724; }
        .status.inactive { background: #f8d7da; color: #721c24; }
        .delete-btn { color: #e74c3c; cursor: pointer; font-size: 18px; border: none; background: none; }
    </style>
</head>
<body x-data="dashboard" x-init="fetchAll()">
    <div class="container">
        <div class="header">
            <h1>Tushare 智能选股 Agent</h1>
            <nav>
                <a href="/">仪表盘</a>
                <a href="/chat">智能对话</a>
            </nav>
        </div>

        <div class="cards">
            <div class="card"><h3>策略总数</h3><div class="value" x-text="summary.strategy_count || '--'">--</div></div>
            <div class="card"><h3>启用策略</h3><div class="value" x-text="summary.enabled_count || '--'">--</div></div>
            <div class="card"><h3>最新报告</h3><div class="value" x-text="summary.recent_reports ? summary.recent_reports.length : '--'">--</div></div>
        </div>

        <div class="section">
            <h2>选股策略</h2>
            <template x-if="strategies.length === 0">
                <p style="color:#999">暂无策略，请通过 API 创建</p>
            </template>
            <template x-if="strategies.length > 0">
                <table>
                    <thead><tr><th>名称</th><th>调度</th><th>状态</th><th>操作</th></tr></thead>
                    <tbody>
                        <template x-for="s in strategies" :key="s.id">
                            <tr>
                                <td x-text="s.name"></td>
                                <td x-text="s.schedule"></td>
                                <td>
                                    <span class="status" :class="s.enabled ? 'active' : 'inactive'"
                                          x-text="s.enabled ? '启用' : '禁用'"></span>
                                </td>
                                <td>
                                    <button class="delete-btn" @click="deleteStrategy(s.id)" title="删除">&times;</button>
                                </td>
                            </tr>
                        </template>
                    </tbody>
                </table>
            </template>
        </div>

        <div class="section">
            <h2>最新报告</h2>
            <template x-if="reports.length === 0">
                <p style="color:#999">暂无报告，等待定时任务执行或手动触发</p>
            </template>
            <template x-if="reports.length > 0">
                <table>
                    <thead><tr><th>类型</th><th>摘要</th><th>时间</th></tr></thead>
                    <tbody>
                        <template x-for="r in reports" :key="r.id">
                            <tr>
                                <td x-text="r.type === 'screening' ? '选股' : '基本面'"></td>
                                <td x-text="r.summary_text || r.summary || '(点击查看详情)'"></td>
                                <td x-text="r.created_at?.slice(0, 16)"></td>
                            </tr>
                        </template>
                    </tbody>
                </table>
            </template>
        </div>
    </div>

    <script>
        document.addEventListener('alpine:init', () => {
            Alpine.data('dashboard', () => ({
                summary: {},
                strategies: [],
                reports: [],

                async fetchAll() {
                    await Promise.all([this.fetchSummary(), this.fetchStrategies(), this.fetchReports()]);
                },

                async fetchSummary() {
                    try {
                        const r = await fetch('/api/dashboard/summary');
                        this.summary = await r.json();
                    } catch(e) {}
                },

                async fetchStrategies() {
                    try {
                        const r = await fetch('/api/strategies');
                        this.strategies = await r.json();
                    } catch(e) {}
                },

                async fetchReports() {
                    try {
                        const r = await fetch('/api/reports?limit=10');
                        this.reports = await r.json();
                    } catch(e) {}
                },

                async deleteStrategy(id) {
                    if (!confirm('确认删除此策略？')) return;
                    try {
                        await fetch(`/api/strategies/${id}`, { method: 'DELETE' });
                        await this.fetchStrategies();
                    } catch(e) {}
                },
            }));
        });
    </script>
</body>
</html>
```

- [ ] **Step 3: 实现对话 HTML 页面**

```html
<!-- app/web/templates/chat.html -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tushare Agent - 对话</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; color: #333; height: 100vh; display: flex; flex-direction: column; }
        .header { background: #1a1a2e; color: white; padding: 15px 20px; display: flex; justify-content: space-between; align-items: center; }
        .header h1 { font-size: 20px; }
        .header nav a { color: #a0a0ff; text-decoration: none; }
        .messages { flex: 1; overflow-y: auto; padding: 20px; max-width: 800px; margin: 0 auto; width: 100%; }
        .msg { margin-bottom: 16px; padding: 12px 16px; border-radius: 8px; max-width: 85%; }
        .msg.user { background: #1a1a2e; color: white; margin-left: auto; }
        .msg.assistant { background: white; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .msg.tool { background: #fff3cd; font-size: 13px; color: #856404; border: 1px solid #ffc107; }
        .input-area { padding: 15px 20px; background: white; border-top: 1px solid #ddd; display: flex; gap: 10px; max-width: 800px; margin: 0 auto; width: 100%; }
        .input-area input { flex: 1; padding: 10px 15px; border: 1px solid #ddd; border-radius: 8px; font-size: 15px; outline: none; }
        .input-area button { padding: 10px 20px; background: #1a1a2e; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 15px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>智能对话</h1>
        <nav><a href="/">← 仪表盘</a></nav>
    </div>
    <div class="messages" id="messages"></div>
    <div class="input-area">
        <input type="text" id="chatInput" placeholder="输入问题，如：帮我分析600519的ROE和PE..." autofocus>
        <button onclick="sendMessage()">发送</button>
    </div>

    <script>
        const messages = document.getElementById('messages');
        const input = document.getElementById('chatInput');

        function addMessage(type, text) {
            const div = document.createElement('div');
            div.className = `msg ${type}`;
            div.textContent = text;
            messages.appendChild(div);
            messages.scrollTop = messages.scrollHeight;
        }

        function addToolMessage(toolName) {
            const div = document.createElement('div');
            div.className = 'msg tool';
            div.textContent = `🔧 调用工具: ${toolName}`;
            messages.appendChild(div);
            messages.scrollTop = messages.scrollHeight;
            return div;
        }

        let currentAssistantMsg = null;

        async function sendMessage() {
            const text = input.value.trim();
            if (!text) return;
            input.value = '';

            addMessage('user', text);
            const resp = await fetch('/api/chat', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({message: text}),
            });

            const reader = resp.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const {done, value} = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, {stream: true});
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            if (data.type === 'tool_call') {
                                addToolMessage(data.tool);
                            } else if (data.type === 'thinking') {
                                if (!currentAssistantMsg) {
                                    const div = document.createElement('div');
                                    div.className = 'msg assistant';
                                    messages.appendChild(div);
                                    currentAssistantMsg = div;
                                }
                                currentAssistantMsg.textContent += data.text;
                                messages.scrollTop = messages.scrollHeight;
                            } else if (data.type === 'done') {
                                currentAssistantMsg = null;
                            }
                        } catch(e) {}
                    }
                }
            }
        }

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    </script>
</body>
</html>
```

- [ ] **Step 4: Commit**

```bash
git add app/web/api/dashboard.py app/web/templates/dashboard.html app/web/templates/chat.html
git commit -m "feat: add dashboard API, dashboard and chat HTML pages"
```

---

## Phase 6: 集成与入口

### Task 17: FastAPI 应用入口

**Files:**
- Create: `app/main.py`

- [ ] **Step 1: 实现应用入口，组装所有模块**

```python
# app/main.py
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import Settings
from app.data.tushare_client import TushareClient
from app.data.cache import CacheManager
from app.data.repository import Repository
from app.agent.router import AgentRouter
from app.agent.tools.tushare_tools import set_tushare_client
from app.scheduler.engine import start_scheduler, shutdown_scheduler, add_daily_job, add_weekly_job
from app.scheduler.jobs import init_jobs, daily_screening_job, weekly_analysis_job
from app.notify.email_sender import EmailSender
from app.notify.wechat_bot import WeChatBot
from app.web.api import strategies as strategies_api
from app.web.api import reports as reports_api
from app.web.api import chat as chat_api
from app.web.api import dashboard as dashboard_api

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = Settings()
templates = Jinja2Templates(directory="app/web/templates")

# 初始化各层
cache = CacheManager()
tushare_client = TushareClient(token=settings.TUSHARE_TOKEN)
set_tushare_client(tushare_client)

repo = Repository(database_url=settings.DATABASE_URL)
router = AgentRouter(settings)
email_sender = EmailSender(
    host=settings.SMTP_HOST, port=settings.SMTP_PORT,
    user=settings.SMTP_USER, password=settings.SMTP_PASSWORD,
    from_addr=settings.SMTP_FROM,
)
wechat_bot = WeChatBot(webhook_url=settings.WECHAT_WEBHOOK_URL)

# 注入依赖到各 API 模块
strategies_api.init(repo)
reports_api.init(repo)
chat_api.init(router)
dashboard_api.init(repo)
init_jobs(repo, router)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("启动调度器...")
    start_scheduler(settings.DATABASE_URL)
    hour, minute = settings.SCHEDULER_DAILY_SCREEN_TIME.split(":")
    add_daily_job(daily_screening_job, int(hour), int(minute), "daily_screening")
    dow = settings.SCHEDULER_WEEKLY_ANALYSIS_DAY
    wh, wm = settings.SCHEDULER_WEEKLY_ANALYSIS_TIME.split(":")
    add_weekly_job(weekly_analysis_job, dow, int(wh), int(wm), "weekly_analysis")
    logger.info("调度器已启动")

    # 首次启动预热：同步股票池
    try:
        df = tushare_client.get_stock_basic()
        if not df.empty:
            stocks = [
                {"ts_code": r["ts_code"], "name": r["name"],
                 "industry": r.get("industry", ""), "list_date": r.get("list_date")}
                for _, r in df.iterrows()
            ]
            repo.upsert_stocks(stocks)
            logger.info(f"股票池已初始化，共 {len(stocks)} 只")
    except Exception as e:
        logger.warning(f"股票池初始化失败（可能 Tushare Token 未配置）: {e}")

    yield

    # Shutdown
    logger.info("关闭调度器...")
    shutdown_scheduler()


app = FastAPI(title="Tushare Agent", lifespan=lifespan)

# 挂载 API 路由
app.include_router(strategies_api.router)
app.include_router(reports_api.router)
app.include_router(chat_api.router)
app.include_router(dashboard_api.router)


@app.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 2: 验证应用可启动**

```bash
# 检查导入是否正确（不实际运行）
python -c "from app.main import app; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: add FastAPI application entry point with lifecycle management"
```

---

### Task 18: 端到端验证

- [ ] **Step 1: 安装依赖并启动应用**

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- [ ] **Step 2: 验证 API 端点**

```bash
# 健康检查
curl http://localhost:8000/health

# 仪表盘摘要
curl http://localhost:8000/api/dashboard/summary

# 查看页面
curl http://localhost:8000/
curl http://localhost:8000/chat
```

- [ ] **Step 3: 创建第一个策略并手动触发**

```bash
curl -X POST http://localhost:8000/api/strategies \
  -H "Content-Type: application/json" \
  -d '{
    "name": "低估值高ROE",
    "conditions": {
      "pe_max": 25,
      "pb_max": 3,
      "roe_min": 15,
      "revenue_growth_min": 5,
      "profit_growth_min": 5,
      "industry_exclude": ["房地产"],
      "top_n": 10
    }
  }'
```

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "chore: final integration and verification"
```

---

## 任务依赖关系

```
Phase 1: Task 1 → Task 2
Phase 2: Task 3 → Task 4 → Task 5 → Task 6
Phase 3: Task 7 → Task 8 → Task 9 → Task 10 → Task 11
Phase 4: Task 12, Task 13 (并行)
Phase 5: Task 14 → Task 15 → Task 16
Phase 6: Task 17 → Task 18
```

- Phase 3 依赖 Phase 2（Agent 需要 Data 层）
- Phase 4 依赖 Phase 3（Scheduler 需要 Agent Router）
- Phase 5 依赖 Phase 2 + Phase 3（Web API 需要 Repository 和 Agent Router）
- Phase 6 依赖全部前序 Phase

## 关键依赖顺序

```
config → models → tushare_client → cache → repository
                                         ↓
                          tushare_tools → prompts → chains → router
                                                              ↓
                                          scheduler (engine + jobs)
                                          notify (email + wechat)
                                                              ↓
                          web api (strategies + reports + chat + dashboard)
                                                              ↓
                                                          main.py
```
