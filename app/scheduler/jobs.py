import logging
from datetime import datetime, timezone

from app.data.repository import Repository
from app.data.models import TaskStatus, ReportType
from app.agent.router import AgentRouter
from app.notify.email_sender import EmailSender
from app.notify.wechat_bot import WeChatBot
from app.strategies.qiangshigu import QiangshiguStrategy

logger = logging.getLogger(__name__)

_repo: Repository | None = None
_router: AgentRouter | None = None
_email_sender: EmailSender | None = None
_wechat_bot: WeChatBot | None = None
_pro = None  # tushare pro_api instance
_strategies: dict = {}  # name -> strategy instance


def init_jobs(
    repo: Repository,
    router: AgentRouter,
    pro,
    email_sender: EmailSender | None = None,
    wechat_bot: WeChatBot | None = None,
) -> None:
    global _repo, _router, _pro, _email_sender, _wechat_bot, _strategies
    _repo = repo
    _router = router
    _pro = pro
    _email_sender = email_sender
    _wechat_bot = wechat_bot
    _strategies = {
        "强势股回调战法": QiangshiguStrategy(),
    }


async def daily_screening_job() -> None:
    """日频选股任务：算法筛选 + LLM解读 + 推送"""
    if _repo is None or _router is None or _pro is None:
        logger.error("Jobs not initialized")
        return

    strategies = _repo.list_strategies(enabled_only=True)
    logger.info(f"日频选股开始，共 {len(strategies)} 个策略")

    for st in strategies:
        try:
            task_run = _repo.create_task_run(st.id)
            _repo.update_task_run(task_run.id, status=TaskStatus.RUNNING)

            # Step 1: 算法筛选
            strategy = _strategies.get(st.name)
            if strategy is None:
                logger.warning(f"未找到策略插件: {st.name}，跳过")
                continue

            from datetime import datetime as dt, timedelta
            end_date = dt.now().strftime("%Y%m%d")
            start_date = (dt.now() - timedelta(days=60)).strftime("%Y%m%d")

            df = strategy.run(_pro, start_date, end_date)
            screening_data = df.to_dict(orient="records") if len(df) > 0 else []

            # Step 2: LLM解读
            if screening_data:
                summary = _router.generate_report("screening", screening_data)
            else:
                summary = "本次筛选未找到符合条件的股票。"

            # Step 3: 持久化
            _repo.create_report(task_run.id, ReportType.SCREENING, screening_data, summary)
            _repo.update_task_run(task_run.id, status=TaskStatus.DONE, finished_at=datetime.now(timezone.utc))
            logger.info(f"策略「{st.name}」执行完成，筛选出 {len(screening_data)} 只，报告ID: {task_run.id}")

            # Step 4: 推送通知
            if _email_sender and _email_sender.enabled:
                _email_sender.send(
                    to="user@example.com",
                    subject=f"[Tushare Agent] {st.name} 选股报告",
                    html_body=f"<h2>{st.name}</h2><pre>{summary}</pre>",
                )
            if _wechat_bot and _wechat_bot.enabled:
                _wechat_bot.send_markdown(f"## {st.name} 选股报告\n\n{summary}")

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
        strategy_list = _repo.list_strategies(enabled_only=True)
        st_id = strategy_list[0].id if strategy_list else None
        if st_id is None:
            return
        task_run = _repo.create_task_run(st_id)
        _repo.update_task_run(task_run.id, status=TaskStatus.RUNNING)

        result = _router.run_fundamental_for_stocks(codes)
        summary = _router.generate_report("fundamental", result)
        _repo.create_report(task_run.id, ReportType.FUNDAMENTAL, result, summary)

        _repo.update_task_run(task_run.id, status=TaskStatus.DONE, finished_at=datetime.now(timezone.utc))
        logger.info("周频分析完成")

        # 推送通知
        if _wechat_bot and _wechat_bot.enabled:
            _wechat_bot.send_markdown(f"## 周频基本面分析报告\n\n{summary}")
    except Exception as e:
        logger.error(f"周频分析失败: {e}")
