import json
from langchain_deepseek import ChatDeepSeek
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

from app.agent.tools.tushare_tools import (
    get_stock_basic, get_financial_indicators, get_daily_basic, get_income_statement,
    get_industry_list, get_trade_calendar,
)

FUNDAMENTAL_PROMPT_FILE = "app/agent/prompts/fundamental.txt"


def _load_prompt() -> str:
    with open(FUNDAMENTAL_PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()


def build_fundamental_executor(llm: ChatDeepSeek) -> AgentExecutor:
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


def run_fundamental(executor: AgentExecutor, stock_codes: list[str]) -> dict:
    codes_str = ", ".join(stock_codes)
    input_text = f"请对以下股票进行基本面分析：{codes_str}。请为每只股票输出深度分析。"
    result = executor.invoke({"input": input_text})
    return {"stocks": stock_codes, "output": result["output"]}
