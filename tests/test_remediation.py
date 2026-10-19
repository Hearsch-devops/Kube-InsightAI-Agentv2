
import pytest

from app.mcp.remediation import build_remediation_proposal


def test_deployment_restart_proposal():
    proposal = build_remediation_proposal(
        "Restart deployment kube-insightaiv2-agent "
        "in namespace kube-insightaiv2"
    )

    assert proposal is not None
    assert proposal["action"] == "restart_deployment"
    assert proposal["status"] == "proposed"
    assert proposal["resource_kind"] == "Deployment"
    assert proposal["resource_name"] == "kube-insightaiv2-agent"
    assert proposal["deployment"] == "kube-insightaiv2-agent"
    assert proposal["namespace"] == "kube-insightaiv2"
    assert proposal["execution_enabled"] is False


def test_unschedulable_pod_proposal():
    proposal = build_remediation_proposal(
        "Propose remediation for unschedulable pod "
        "scenario-5-unschedulable in namespace testing-files"
    )

    assert proposal is not None
    assert proposal["action"] == "review_pod_scheduling"
    assert proposal["status"] == "proposed"
    assert proposal["resource_kind"] == "Pod"
    assert proposal["resource_name"] == "scenario-5-unschedulable"
    assert proposal["deployment"] is None
    assert proposal["namespace"] == "testing-files"
    assert proposal["execution_enabled"] is False


def test_missing_pod_name_requests_clarification():
    proposal = build_remediation_proposal(
        "Prepare a remediation proposal for pod scheduling "
        "in namespace testing-files"
    )

    assert proposal is not None
    assert proposal["status"] == "needs_clarification"
    assert proposal["resource_kind"] == "Pod"
    assert proposal["namespace"] == "testing-files"
    assert proposal["execution_enabled"] is False


def test_missing_namespace_requests_clarification():
    proposal = build_remediation_proposal(
        "Restart deployment kube-insightaiv2-agent"
    )

    assert proposal is not None
    assert proposal["status"] == "needs_clarification"
    assert proposal["resource_kind"] == "Deployment"
    assert proposal["execution_enabled"] is False


@pytest.mark.parametrize(
    "question",
    [
        "What pods are currently running in namespace testing-files?",
        "List deployments in namespace kube-insightaiv2",
        "Explain Kubernetes scheduling",
    ],
)
def test_regular_questions_do_not_create_proposals(question):
    assert build_remediation_proposal(question) is None
