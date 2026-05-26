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

    async def event_generator():
        async for event in _router.run_query_stream(req.message):
            yield {"event": "message", "data": event.replace("data: ", "")}

    return EventSourceResponse(event_generator())
