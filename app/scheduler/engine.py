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
