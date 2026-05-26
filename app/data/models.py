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
