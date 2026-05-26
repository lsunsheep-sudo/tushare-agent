import json
from typing import AsyncIterator
from langchain_deepseek import ChatDeepSeek
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

from app.agent.tools.tushare_tools import (
    get_stock_basic, get_financial_indicators, get_daily_basic, get_income_statement,
    get_industry_list, get_trade_calendar,
)

QUERY_PROMPT_FILE = "app/agent/prompts/query.txt"


def _load_prompt() -> str:
    with open(QUERY_PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()


def build_query_executor(llm: ChatDeepSeek) -> AgentExecutor:
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


async def run_query_stream(executor: AgentExecutor, message: str) -> AsyncIterator[str]:
    """流式执行自由问答，yield SSE 事件字符串"""
    async for event in executor.astream_events({"input": message}, version="v2"):
        kind = event.get("event", "")
        if kind == "on_tool_start":
            tool_name = event.get("name", "unknown")
            yield f'data: {{"type": "tool_call", "tool": "{tool_name}"}}\n\n'
        elif kind == "on_tool_end":
            yield f'data: {{"type": "tool_result", "tool": "{event.get("name", "unknown")}"}}\n\n'
        elif kind == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk", None)
            if chunk and hasattr(chunk, "content") and chunk.content:
                yield f'data: {{"type": "thinking", "text": {json.dumps(chunk.content, ensure_ascii=False)}}}\n\n'

    yield 'data: {"type": "done"}\n\n'
