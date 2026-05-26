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
