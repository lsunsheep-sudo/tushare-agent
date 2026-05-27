import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

# ── Initialize all layers ──

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

# ── Inject dependencies ──

strategies_api.init(repo)
reports_api.init(repo)
chat_api.init(router)
dashboard_api.init(repo)
init_jobs(repo, router, tushare_client.pro, email_sender, wechat_bot)


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

    # Warm up: sync stock pool
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


app = FastAPI(title="Tushare Agent API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Mount API routes ──

app.include_router(strategies_api.router)
app.include_router(reports_api.router)
app.include_router(chat_api.router)
app.include_router(dashboard_api.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
