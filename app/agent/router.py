import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from langchain_deepseek import ChatDeepSeek

from app.agent.chains.screening import build_screening_executor, run_screening
from app.agent.chains.fundamental import build_fundamental_executor, run_fundamental
from app.agent.chains.query import build_query_executor, run_query_stream
from app.agent.chains.report import generate_report
from app.strategies.qiangshigu import QiangshiguStrategy

STOCK_CODE_PATTERN = re.compile(r"\b(6\d{5}|0\d{5}|3\d{5})\b")
STRATEGY_KEYWORDS = [
    "筛选", "选股", "海选", "扫描", "策略", "筛", "选",
    "执行策略", "运行策略", "开始选股",
]


@dataclass
class RouteResult:
    chain: str  # "screening", "fundamental", "query"
    input_text: str
    strategy_name: str | None = None
    conditions: dict | None = None
    stock_codes: list[str] | None = None


class AgentRouter:
    def __init__(self, settings):
        self._llm = ChatDeepSeek(
            model=settings.DEEPSEEK_MODEL,
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            temperature=0.3,
        )
        self._screening_exec = build_screening_executor(self._llm)
        self._fundamental_exec = build_fundamental_executor(self._llm)
        self._query_exec = build_query_executor(self._llm)
        self._pro = None
        self._strategies: dict = {}

    def classify(self, message: str) -> RouteResult:
        """分类用户输入，返回路由结果"""
        for kw in STRATEGY_KEYWORDS:
            if kw in message:
                return RouteResult(chain="screening", input_text=message)

        codes = STOCK_CODE_PATTERN.findall(message)
        if codes:
            return RouteResult(chain="fundamental", input_text=message, stock_codes=list(set(codes)))

        return RouteResult(chain="query", input_text=message)

    def set_strategies(self, pro, strategies: dict) -> None:
        self._pro = pro
        self._strategies = strategies

    def run_strategy_for_message(self, message: str) -> str | None:
        """If message triggers a strategy, run it and return LLM report. Returns None if no strategy matched."""
        # Simple keyword matching against known strategy names
        for name, strategy in self._strategies.items():
            if name in message:
                return self._run_strategy(name, strategy)
        # Also check for generic screening requests
        for kw in ["强势股", "回调", "选股"]:
            if kw in message:
                # Default to qiangshigu if keywords match
                strategy = self._strategies.get("强势股回调战法")
                if strategy:
                    return self._run_strategy("强势股回调战法", strategy)
                break
        return None

    def _run_strategy(self, name: str, strategy) -> str:
        """Execute a strategy and generate LLM report."""
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=60)).strftime("%Y%m%d")
        df = strategy.run(self._pro, start_date, end_date)
        records = df.to_dict(orient="records") if len(df) > 0 else []
        if not records:
            return f"「{name}」策略执行完成，当前市场未找到符合条件的股票。"
        return generate_report(self._llm, "screening", records)

    def run_screening_for_strategy(self, strategy_name: str, conditions: dict) -> dict:
        return run_screening(self._screening_exec, strategy_name, conditions)

    def run_fundamental_for_stocks(self, stock_codes: list[str]) -> dict:
        return run_fundamental(self._fundamental_exec, stock_codes)

    async def run_query_stream(self, message: str):
        async for event in run_query_stream(self._query_exec, message):
            yield event

    def generate_report(self, analysis_type: str, raw_data: dict) -> str:
        return generate_report(self._llm, analysis_type, raw_data)

    @property
    def llm(self):
        return self._llm
