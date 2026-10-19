
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import (
    Base,
    ApprovalDecision,
    AuditEvent,
    RemediationProposal,
    User,
)
from app.api.remediation_routes import (
    DecisionRequest,
    decide_proposal,
    proposal_response,
)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    with TestingSession() as session:
        yield session

    Base.metadata.drop_all(engine)
    engine.dispose()


def add_proposal(db, resource_kind, resource_name):
    proposal = RemediationProposal(
        action=(
            "restart_deployment"
            if resource_kind == "Deployment"
            else "review_pod_scheduling"
        ),
        namespace="test-namespace",
        deployment=(
            resource_name if resource_kind == "Deployment" else ""
        ),
        resource_kind=resource_kind,
        resource_name=resource_name,
        reason="Automated test proposal",
        status="proposed",
        execution_enabled=False,
        requested_by="test-admin",
    )
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return proposal


@pytest.mark.parametrize(
    ("kind", "name", "expected_deployment"),
    [
        ("Deployment", "demo-agent", "demo-agent"),
        ("Pod", "demo-pod", None),
    ],
)
def test_proposal_response_resource_fields(
    db, kind, name, expected_deployment
):
    proposal = add_proposal(db, kind, name)

    response = proposal_response(proposal)

    assert response["resource_kind"] == kind
    assert response["resource_name"] == name
    assert response["deployment"] == expected_deployment
    assert response["execution_enabled"] is False


@pytest.mark.parametrize(
    ("decision", "expected_status", "expected_event"),
    [
        ("approve", "approved", "proposal_approved"),
        ("reject", "rejected", "proposal_rejected"),
    ],
)
@pytest.mark.parametrize(
    ("kind", "name"),
    [
        ("Deployment", "demo-agent"),
        ("Pod", "demo-pod"),
    ],
)
def test_decision_records_audit_without_execution(
    db, decision, expected_status, expected_event, kind, name
):
    proposal = add_proposal(db, kind, name)
    user = User(
        username="test-approver",
        role="approver",
        password_hash="not-used-in-this-test",
    )

    response = decide_proposal(
        proposal.id,
        decision,
        DecisionRequest(comment="API behavior test"),
        db,
        user,
    )

    assert response["status"] == expected_status
    assert response["resource_kind"] == kind
    assert response["resource_name"] == name
    assert response["execution_enabled"] is False

    saved = db.get(RemediationProposal, proposal.id)
    assert saved.status == expected_status
    assert saved.execution_enabled is False

    decisions = db.scalars(
        select(ApprovalDecision).where(
            ApprovalDecision.proposal_id == proposal.id
        )
    ).all()
    assert len(decisions) == 1
    assert decisions[0].decision == decision
    assert decisions[0].comment == "API behavior test"

    events = db.scalars(
        select(AuditEvent).where(
            AuditEvent.proposal_id == proposal.id
        )
    ).all()
    decision_events = [
        event for event in events
        if event.event_type == expected_event
    ]
    assert len(decision_events) == 1

    details = decision_events[0].details
    assert details["resource_kind"] == kind
    assert details["resource_name"] == name
    assert details["execution_enabled"] is False


def test_cannot_decide_proposal_twice(db):
    proposal = add_proposal(db, "Pod", "demo-pod")
    user = User(
        username="test-approver",
        role="approver",
        password_hash="not-used-in-this-test",
    )

    decide_proposal(
        proposal.id, "approve", DecisionRequest(), db, user
    )

    with pytest.raises(HTTPException) as exc:
        decide_proposal(
            proposal.id, "reject", DecisionRequest(), db, user
        )

    assert exc.value.status_code == 409
