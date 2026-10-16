
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, update
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

@router.get(
    "/proposals/{proposal_id}",
    response_model=ProposalResponse,
)
def get_proposal(
    proposal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    proposal = db.get(RemediationProposal, proposal_id)

    if proposal is None:
        raise HTTPException(
            status_code=404,
            detail="Proposal not found",
        )

    return proposal_response(proposal)

@router.get("/proposals/{proposal_id}/history")
def get_proposal_history(
    proposal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "approver")),
):
    proposal = db.get(RemediationProposal, proposal_id)

    if proposal is None:
        raise HTTPException(
            status_code=404,
            detail="Proposal not found",
        )

    decisions = db.scalars(
        select(ApprovalDecision)
        .where(ApprovalDecision.proposal_id == proposal_id)
        .order_by(ApprovalDecision.decided_at.desc())
    ).all()

    events = db.scalars(
        select(AuditEvent)
        .where(AuditEvent.proposal_id == proposal_id)
        .order_by(AuditEvent.created_at.desc())
    ).all()

    return {
        "proposal": proposal_response(proposal),
        "decisions": [
            {
                "id": item.id,
                "decided_by": item.decided_by,
                "decision": item.decision,
                "comment": item.comment,
                "decided_at": item.decided_at.isoformat(),
            }
            for item in decisions
        ],
        "audit_events": [
            {
                "id": item.id,
                "actor": item.actor,
                "event_type": item.event_type,
                "details": item.details,
                "created_at": item.created_at.isoformat(),
            }
            for item in events
        ],
    }

def decide_proposal(
    proposal_id: int,
    decision: Decision,
    payload: DecisionRequest,
    db: Session,
    current_user: User,
) -> dict:
    if decision not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Invalid decision")

    new_status = "approved" if decision == "approve" else "rejected"
    event_type = (
        "proposal_approved"
        if decision == "approve"
        else "proposal_rejected"
    )

    try:
        # Atomically change status only if the proposal is still pending.
        result = db.execute(
            update(RemediationProposal)
            .where(
                RemediationProposal.id == proposal_id,
                RemediationProposal.status == "proposed",
            )
            .values(
                status=new_status,
                execution_enabled=False,
            )
            .execution_options(synchronize_session=False)
        )

        if result.rowcount != 1:
            db.rollback()

            proposal_exists = db.scalar(
                select(RemediationProposal.id).where(
                    RemediationProposal.id == proposal_id
                )
            )

            if proposal_exists is None:
                raise HTTPException(
                    status_code=404,
                    detail="Proposal not found",
                )

            raise HTTPException(
                status_code=409,
                detail="Proposal has already been decided",
            )

        # Read the persisted proposal values for the audit record.
        proposal = db.get(RemediationProposal, proposal_id)
        if proposal is None:
            db.rollback()
            raise HTTPException(
                status_code=404,
                detail="Proposal not found",
            )

        db.add(
            ApprovalDecision(
                proposal_id=proposal_id,
                decided_by=current_user.username,
                decision=decision,
                comment=payload.comment,
            )
        )

        db.add(
            AuditEvent(
                proposal_id=proposal_id,
                actor=current_user.username,
                event_type=event_type,
                details={
                    "decision": decision,
                    "namespace": proposal.namespace,
                    "deployment": proposal.deployment,
                    "execution_enabled": False,
                },
            )
        )

        db.commit()

        # Refresh so the response reflects the committed state.
        db.refresh(proposal)
        return proposal_response(proposal)

    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise

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
