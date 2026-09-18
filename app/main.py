import logging

from fastapi import FastAPI
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage

from app.langgraph.graph import graph


logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

app = FastAPI(title="Kube-InsightAI")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    response: str
    route: str | None = None
    analysis: str | None = None
    sources: list[str] = []
    error: str | None = None


@app.get("/")
async def health_check():
    return {
        "status": "ok",
        "service": "Kube-InsightAI",
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a user question through the LangGraph and RAG workflow."""

    logger.info("Received chat request")

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

        return ChatResponse(
            response="An error occurred while processing your request.",
            error="Internal agent error",
        )
