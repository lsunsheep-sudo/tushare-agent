import json
from langchain_deepseek import ChatDeepSeek
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

from app.agent.tools.tushare_tools import (
    get_stock_basic, get_financial_indicators, get_daily_basic, get_income_statement,
    get_industry_list, get_trade_calendar,
)

SCREENING_PROMPT_FILE = "app/agent/prompts/screening.txt"


def _load_prompt() -> str:
    with open(SCREENING_PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()


def build_screening_executor(llm: ChatDeepSeek) -> AgentExecutor:
    tools = [
        get_stock_basic, get_financial_indicators, get_daily_basic,
        get_income_statement, get_industry_list, get_trade_calendar,
    ]
    system_prompt = _load_prompt()
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True, max_iterations=10)


def run_screening(executor: AgentExecutor, strategy_name: str, conditions: dict) -> dict:
    conditions_str = json.dumps(conditions, ensure_ascii=False)
    input_text = (
        f"请执行选股策略「{strategy_name}」，筛选条件如下：\n{conditions_str}\n\n"
        f"请输出排名前 {conditions.get('top_n', 20)} 的股票，格式为 JSON 数组，"
        f"每项包含 ts_code、name、industry、rank、score (0-100)、metrics (pe、pb、roe等关键值)。"
    )
    result = executor.invoke({"input": input_text})
    return {"strategy": strategy_name, "conditions": conditions, "output": result["output"]}
