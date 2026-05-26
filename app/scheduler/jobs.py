import logging
from datetime import datetime, timezone

from app.data.repository import Repository
from app.data.models import TaskStatus, ReportType
from app.agent.router import AgentRouter

logger = logging.getLogger(__name__)

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

    codes = [s.ts_code for s in stocks[:20]]
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
