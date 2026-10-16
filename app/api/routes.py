from app.database import (
    SessionLocal,
    RemediationProposal,
    AuditEvent,
)

from app.mcp_client import (
    call_mcp_tool,
    parse_mcp_result,
    KUBERNETES_MCP_URL,
)
import json
import logging
import os

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from app.auth import get_current_user
from app.database import User

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
    sources: list[str] = Field(default_factory=list)
    error: str | None = None
    error_message: str | None = None
    remediation_proposal: dict | None = None

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
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

        proposal = result.get("remediation_proposal")

        if isinstance(proposal, dict):
            result["remediation_proposal"] = persist_remediation_proposal(
            proposal,
            requested_by=current_user.username,
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
            error_message=result.get("error_message"),
            remediation_proposal=result.get("remediation_proposal"),
        )

    except Exception:
        logger.exception("Chat request failed")

        raise HTTPException(
            status_code=500,
            detail="An internal error occurred while processing the request.",
        )

# ============================================================
# helper to persist proposals
# ============================================================

def persist_remediation_proposal(
    proposal: dict,
    requested_by: str,
) -> dict:
    """Persist a valid proposal without executing any Kubernetes operation."""

    if proposal.get("status") != "proposed":
        return proposal

    action = proposal.get("action")
    deployment = proposal.get("deployment")
    namespace = proposal.get("namespace")

    if (
        action != "restart_deployment"
        or not isinstance(deployment, str)
        or not isinstance(namespace, str)
        or not deployment
        or not namespace
    ):
        raise ValueError("Invalid remediation proposal.")

    # Enforce proposal-only behavior on the backend.
    proposal_record = {
        **proposal,
        "execution_enabled": False,
    }

    with SessionLocal() as db:
        try:
            record = RemediationProposal(
                action=action,
                namespace=namespace,
                deployment=deployment,
                reason=str(proposal.get("reason", "")),
                status="proposed",
                execution_enabled=False,
                requested_by=requested_by,  # Username from the authenticated request.
            )

            db.add(record)
            db.flush()

            audit_event = AuditEvent(
                proposal_id=record.id,
                actor=requested_by,
                event_type="proposal_created",
                details={
                    "action": action,
                    "namespace": namespace,
                    "deployment": deployment,
                    "execution_enabled": False,
                },
            )

            db.add(audit_event)
            db.commit()

            proposal_record["id"] = record.id
            return proposal_record

        except Exception:
            db.rollback()
            raise

# ============================================================
# Kubernetes MCP Configuration
# ============================================================

KUBERNETES_MCP_URL = os.getenv(
    "KUBERNETES_MCP_URL",
    "http://kube-insightaiv2-mcp:8001/mcp",
)

# ============================================================
# Kubernetes Namespaces
# ============================================================

@router.get("/cluster/namespaces")
async def get_namespaces(
    current_user: User = Depends(get_current_user),
):

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
    current_user: User = Depends(get_current_user),
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
async def get_cluster_metrics(
    current_user: User = Depends(get_current_user),
):

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

# ============================================================
# Kubernetes Ingresses
# ============================================================

@router.get("/cluster/ingresses")
async def get_cluster_ingresses(
    namespace: str | None = None,
    current_user: User = Depends(get_current_user),
):
    try:
        result = await call_mcp_tool(
            KUBERNETES_MCP_URL,
            "list_ingresses",
            {
                "namespace": namespace,
            },
        )

        return {
            "namespace": namespace,
            "ingresses": parse_mcp_result(result),
        }

    except Exception as exc:
        logger.exception(
            "Failed to retrieve Kubernetes ingresses"
        )

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )