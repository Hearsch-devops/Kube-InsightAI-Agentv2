import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage

from app.langgraph.graph import graph


logger = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    response: str
    route: str | None = None
    analysis: str | None = None
    sources: list[str] = []
    error: str | None = None


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Process a user question through the Kube-InsightAI LangGraph workflow."""

    try:
        result = await graph.ainvoke(
            {
                "messages": [
                    HumanMessage(content=request.message)
                ],
                "question": request.message,
            }
        )

        answer = result.get("answer")

        if not answer:
            messages = result.get("messages", [])

            if messages:
                answer = str(messages[-1].content)
            else:
                answer = "The agent could not generate a response."

        return ChatResponse(
            response=answer,
            route=result.get("route"),
            analysis=result.get("analysis"),
            sources=result.get("sources", []),
            error=result.get("error"),
        )

    except Exception:
        logger.exception("Chat request failed")

        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while processing the request.",
        )
