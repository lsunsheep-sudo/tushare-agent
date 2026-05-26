# app/config.py
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # DeepSeek
    DEEPSEEK_API_KEY: str = Field(min_length=1)
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # Tushare
    TUSHARE_TOKEN: str = Field(min_length=1)

    # Database
    DATABASE_URL: str = "postgresql://user:pass@localhost:5432/tushare"

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
