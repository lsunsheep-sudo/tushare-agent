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
