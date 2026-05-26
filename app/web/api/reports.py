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
