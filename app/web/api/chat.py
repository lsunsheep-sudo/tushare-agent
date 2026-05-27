import logging
from fastapi import APIRouter, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.agent.router import AgentRouter

router = APIRouter(prefix="/api", tags=["chat"])

logger = logging.getLogger(__name__)

_router: AgentRouter | None = None


def init(router_: AgentRouter) -> None:
    global _router
    _router = router_


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
async def chat(req: ChatRequest):
    """SSE 流式对话接口"""
    if _router is None:
        return {"error": "Agent not initialized"}

    # Check for strategy execution intent first
    strategy_result = _router.run_strategy_for_message(req.message)
    if strategy_result is not None:
        async def strategy_generator():
            # Stream the report text word by word for SSE effect
            for chunk in strategy_result:
                yield {"event": "message", "data": chunk}
        return EventSourceResponse(strategy_generator())

    # Fall through to general query
    async def event_generator():
        async for event in _router.run_query_stream(req.message):
            yield {"event": "message", "data": event.replace("data: ", "")}

    return EventSourceResponse(event_generator())
