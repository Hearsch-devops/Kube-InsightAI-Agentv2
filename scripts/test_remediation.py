
from app.mcp.remediation import build_remediation_proposal


def test_explicit_restart_creates_proposal_only():
    result = build_remediation_proposal(
        "Restart deployment my-app in namespace testing-files"
    )

    assert result is not None
    assert result["action"] == "restart_deployment"
    assert result["deployment"] == "my-app"
    assert result["namespace"] == "testing-files"
    assert result["status"] == "proposed"
    assert result["execution_enabled"] is False


def test_missing_namespace_requires_clarification():
    result = build_remediation_proposal(
        "Restart deployment my-app"
    )

    assert result is not None
    assert result["status"] == "needs_clarification"
    assert result["execution_enabled"] is False


def test_diagnostic_question_does_not_create_restart_proposal():
    result = build_remediation_proposal(
        "Why is deployment my-app unhealthy in namespace testing-files?"
    )

    assert result is None


def test_unrelated_question_does_not_create_proposal():
    result = build_remediation_proposal(
        "Why do we use Kubernetes?"
    )

    assert result is None


def test_invalid_deployment_name_requires_clarification():
    result = build_remediation_proposal(
        "Restart deployment Bad_Name in namespace testing-files"
    )

    assert result is not None
    assert result["status"] == "needs_clarification"
    assert result["execution_enabled"] is False


def test_invalid_namespace_requires_clarification():
    result = build_remediation_proposal(
        "Restart deployment my-app in namespace Bad_Name"
    )

    assert result is not None
    assert result["status"] == "needs_clarification"
    assert result["execution_enabled"] is False


def test_valid_hyphenated_names_create_proposal():
    result = build_remediation_proposal(
        "Restart deployment scenario-5-unschedulable "
        "in namespace testing-files"
    )

    assert result is not None
    assert result["status"] == "proposed"
    assert result["deployment"] == "scenario-5-unschedulable"
    assert result["namespace"] == "testing-files"
    assert result["execution_enabled"] is False
