import json
import logging
import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage

from app.langgraph.graph import graph
from app.mcp_client import call_mcp_tool


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

# ============================================================
# Kubernetes MCP Configuration
# ============================================================

KUBERNETES_MCP_URL = os.getenv(
    "KUBERNETES_MCP_URL",
    "http://kube-insightaiv2-mcp:8001/mcp",
)


# ============================================================
# MCP Helper
# ============================================================

def parse_mcp_result(result):
    """
    Convert MCP CallToolResult into a JSON-compatible
    Python object.
    """

    if result is None:
        return None

    # Prefer MCP structured content when available.
    if hasattr(result, "structured_content"):
        structured = result.structured_content

        if isinstance(structured, dict) and "result" in structured:
            return structured["result"]

        if structured is not None:
            return structured

    # Fallback to text content for compatibility.
    if hasattr(result, "content"):

        for item in result.content:

            if hasattr(item, "text"):

                text = item.text

                try:
                    return json.loads(text)

                except (json.JSONDecodeError, TypeError):
                    return text

    return result

# ============================================================
# Kubernetes Namespaces
# ============================================================

@router.get("/cluster/namespaces")
async def get_namespaces():

    try:

        result = await call_mcp_tool(
            KUBERNETES_MCP_URL,
            "list_namespaces",
            {},
        )

        data = parse_mcp_result(result)

        return {
            "namespaces": data
        }

    except Exception as exc:

        logger.exception(
            "Failed to retrieve Kubernetes namespaces"
        )

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

# ============================================================
# Kubernetes Cluster Overview
# ============================================================

@router.get("/cluster/overview")
async def get_cluster_overview(
    namespace: str = "kube-insightaiv2",
):

    try:

        pods_result = await call_mcp_tool(
            KUBERNETES_MCP_URL,
            "list_pods",
            {
                "namespace": namespace
            },
        )

        deployments_result = await call_mcp_tool(
            KUBERNETES_MCP_URL,
            "list_deployments",
            {
                "namespace": namespace
            },
        )

        services_result = await call_mcp_tool(
            KUBERNETES_MCP_URL,
            "list_services",
            {
                "namespace": namespace
            },
        )

        events_result = await call_mcp_tool(
            KUBERNETES_MCP_URL,
            "list_events",
            {
                "namespace": namespace,
                "limit": 50,
            },
        )

        return {
            "namespace": namespace,
            "pods": parse_mcp_result(pods_result),
            "deployments": parse_mcp_result(deployments_result),
            "services": parse_mcp_result(services_result),
            "events": parse_mcp_result(events_result),
        }

    except Exception as exc:

        logger.exception(
            "Failed to retrieve Kubernetes cluster overview"
        )

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

# ============================================================
# Kubernetes Cluster Metrics
# ============================================================

@router.get("/cluster/metrics")
async def get_cluster_metrics():

    try:
        result = await call_mcp_tool(
            KUBERNETES_MCP_URL,
            "get_cluster_metrics",
            {},
        )

        return parse_mcp_result(result)

    except Exception as exc:

        logger.exception(
            "Failed to retrieve Kubernetes cluster metrics"
        )

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )