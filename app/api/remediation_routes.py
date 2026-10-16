
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user, get_db, require_roles
from app.database import (
    ApprovalDecision,
    AuditEvent,
    RemediationProposal,
    User,
)

router = APIRouter(prefix="/remediation", tags=["Remediation"])

Decision = Literal["approve", "reject"]


class DecisionRequest(BaseModel):
    comment: str | None = Field(default=None, max_length=2000)


class ProposalResponse(BaseModel):
    id: int
    action: str
    namespace: str
    deployment: str
    reason: str
    status: str
    execution_enabled: bool
    requested_by: str | None
    created_at: str


def proposal_response(proposal: RemediationProposal) -> dict:
    return {
        "id": proposal.id,
        "action": proposal.action,
        "namespace": proposal.namespace,
        "deployment": proposal.deployment,
        "reason": proposal.reason,
        "status": proposal.status,
        "execution_enabled": False,
        "requested_by": proposal.requested_by,
        "created_at": proposal.created_at.isoformat(),
    }


@router.get("/proposals", response_model=list[ProposalResponse])
def list_proposals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    proposals = db.scalars(
        select(RemediationProposal).order_by(
            RemediationProposal.created_at.desc()
        )
    ).all()
    return [proposal_response(item) for item in proposals]


def decide_proposal(
    proposal_id: int,
    decision: Decision,
    payload: DecisionRequest,
    db: Session,
    current_user: User,
) -> dict:
    # Serialize decisions with a row-level lock where the database supports it.
    proposal = db.scalar(
        select(RemediationProposal)
        .where(RemediationProposal.id == proposal_id)
        .with_for_update()
    )

    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")

    if proposal.status != "proposed":
        raise HTTPException(
            status_code=409,
            detail="Proposal has already been decided",
        )

    # Preserve proposal-only mode, regardless of the stored value.
    proposal.execution_enabled = False
    proposal.status = "approved" if decision == "approve" else "rejected"

    db.add(
        ApprovalDecision(
            proposal_id=proposal.id,
            decided_by=current_user.username,
            decision=decision,
            comment=payload.comment,
        )
    )

    db.add(
        AuditEvent(
            proposal_id=proposal.id,
            actor=current_user.username,
            event_type=(
                "proposal_approved"
                if decision == "approve"
                else "proposal_rejected"
            ),
            details={
                "decision": decision,
                "namespace": proposal.namespace,
                "deployment": proposal.deployment,
                "execution_enabled": False,
            },
        )
    )

    db.commit()
    db.refresh(proposal)
    return proposal_response(proposal)


@router.post("/proposals/{proposal_id}/approve", response_model=ProposalResponse)
def approve_proposal(
    proposal_id: int,
    payload: DecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("approver", "admin")),
):
    return decide_proposal(
        proposal_id, "approve", payload, db, current_user
    )


@router.post("/proposals/{proposal_id}/reject", response_model=ProposalResponse)
def reject_proposal(
    proposal_id: int,
    payload: DecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("approver", "admin")),
):
    return decide_proposal(
        proposal_id, "reject", payload, db, current_user
    )
