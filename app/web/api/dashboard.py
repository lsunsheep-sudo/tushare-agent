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
