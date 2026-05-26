# tests/test_config.py
import os
import pytest
from app.config import Settings


class TestSettings:
    def test_defaults(self):
        """默认值：SQLite、标准调度时间"""
        settings = Settings(
            DEEPSEEK_API_KEY="sk-test",
            TUSHARE_TOKEN="test-token",
        )
        assert settings.DATABASE_URL == "sqlite:///./data/tushare.db"
        assert settings.DEEPSEEK_MODEL == "deepseek-chat"
        assert settings.DEEPSEEK_BASE_URL == "https://api.deepseek.com"
        assert settings.SCHEDULER_DAILY_SCREEN_TIME == "15:30"
        assert settings.SCHEDULER_WEEKLY_ANALYSIS_DAY == "fri"
        assert settings.SCHEDULER_WEEKLY_ANALYSIS_TIME == "16:00"

    def test_env_override(self, monkeypatch):
        """环境变量可覆盖默认值"""
        monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/test")
        monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-coder")
        settings = Settings(
            DEEPSEEK_API_KEY="sk-test",
            TUSHARE_TOKEN="test-token",
        )
        assert settings.DATABASE_URL == "postgresql://localhost/test"
        assert settings.DEEPSEEK_MODEL == "deepseek-coder"

    def test_missing_required_raises(self):
        """缺少必填项应报错"""
        with pytest.raises(Exception):
            Settings()  # 缺 DEEPSEEK_API_KEY 和 TUSHARE_TOKEN
