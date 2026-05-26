import json
import os
from langchain_deepseek import ChatDeepSeek
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

_PROMPT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompts")


def _load_prompt() -> str:
    with open(os.path.join(_PROMPT_DIR, "report.txt"), "r", encoding="utf-8") as f:
        return f.read()


def generate_report(llm: ChatDeepSeek, analysis_type: str, raw_data: dict) -> str:
    """将原始分析结果润色为结构化报告文本。"""
    prompt = ChatPromptTemplate.from_messages([
        ("system", _load_prompt()),
        ("human", "分析类型：{analysis_type}\n原始数据：\n{raw_data}\n\n请撰写报告。"),
    ])
    chain = prompt | llm | StrOutputParser()
    result = chain.invoke({
        "analysis_type": analysis_type,
        "raw_data": json.dumps(raw_data, ensure_ascii=False, indent=2),
    })
    return result
