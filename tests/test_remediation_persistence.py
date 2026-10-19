
import os
import subprocess
import sys


def test_deployment_and_pod_proposals_persist_safely(tmp_path):
    db_path = tmp_path / "persistence.db"

    script = r'''
from sqlalchemy import select
from app.database import (
    init_db,
    SessionLocal,
    RemediationProposal,
    AuditEvent,
)
from app.api.routes import persist_remediation_proposal

init_db()

deployment = persist_remediation_proposal(
    {
        "action": "restart_deployment",
        "status": "proposed",
        "resource_kind": "Deployment",
        "resource_name": "demo-agent",
        "deployment": "demo-agent",
        "namespace": "demo",
        "reason": "Deployment restart requested.",
        "execution_enabled": True,
    },
    requested_by="test-admin",
)

pod = persist_remediation_proposal(
    {
        "action": "review_pod_scheduling",
        "status": "proposed",
        "resource_kind": "Pod",
        "resource_name": "scenario-5-unschedulable",
        "namespace": "testing-files",
        "reason": "Review scheduling constraints.",
        "execution_enabled": True,
    },
    requested_by="test-admin",
)

assert deployment["execution_enabled"] is False
assert deployment["deployment"] == "demo-agent"
assert pod["execution_enabled"] is False
assert pod["deployment"] is None
assert pod["resource_kind"] == "Pod"

with SessionLocal() as db:
    records = db.scalars(
        select(RemediationProposal).order_by(RemediationProposal.id)
    ).all()
    assert len(records) == 2

    saved_deployment, saved_pod = records
    assert saved_deployment.resource_kind == "Deployment"
    assert saved_deployment.resource_name == "demo-agent"
    assert saved_deployment.execution_enabled is False

    assert saved_pod.resource_kind == "Pod"
    assert saved_pod.resource_name == "scenario-5-unschedulable"
    assert saved_pod.deployment == ""
    assert saved_pod.execution_enabled is False

    events = db.scalars(select(AuditEvent)).all()
    assert len(events) == 2
    assert all(event.event_type == "proposal_created" for event in events)
    assert all(event.details["execution_enabled"] is False for event in events)

print("Deployment and Pod persistence checks passed")
'''

    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Deployment and Pod persistence checks passed" in result.stdout
