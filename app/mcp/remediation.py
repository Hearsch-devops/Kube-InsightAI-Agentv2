
"""Proposal-only Kubernetes remediation.

This module constructs proposals only. It never executes Kubernetes operations.
"""

import re
from typing import Any


SUPPORTED_ACTIONS = {
    "restart_deployment": "Restart a Kubernetes Deployment",
    "review_pod_scheduling": "Review an unschedulable Pod's scheduling constraints",
}

RESOURCE_NAME_PATTERN = re.compile(
    r"^[a-z0-9](?:[-a-z0-9.]*[a-z0-9])?$"
)


def _extract_target(question: str, resource: str) -> str | None:
    """Extract a named Kubernetes resource from a user request."""
    match = re.search(
        rf"\b{resource}(?:\s+named)?\s+([^\s,;]+)",
        question,
    )
    return match.group(1).rstrip(".,!?") if match else None


def _extract_namespace(question: str) -> str | None:
    match = re.search(r"\bnamespace\s+([^\s,;]+)", question)
    return match.group(1).rstrip(".,!?") if match else None


def build_remediation_proposal(question: str) -> dict[str, Any] | None:
    """Construct a proposal without calling MCP, Kubernetes, or write tools."""
    normalized = question.strip().lower()

    restart_requested = any(
        phrase in normalized
        for phrase in (
            "restart deployment",
            "restart the deployment",
            "restart deployment named",
            "restart the deployment named",
        )
    )

    pod_scheduling_requested = (
        any(
            phrase in normalized
            for phrase in (
                "propose remediation",
                "propose a remediation",
                "prepare a remediation proposal",
                "create a remediation proposal",
                "suggest remediation",
            )
        )
        and any(
            phrase in normalized
            for phrase in (
                "unschedulable pod",
                "pod is unschedulable",
                "pod scheduling",
                "failedscheduling",
                "failed scheduling",
            )
        )
    )

    if not restart_requested and not pod_scheduling_requested:
        return None

    if restart_requested:
        action = "restart_deployment"
        resource = "deployment"
        reason = "The user explicitly requested a Deployment restart."
    else:
        action = "review_pod_scheduling"
        resource = "pod"
        reason = (
            "Review the Pod's scheduling constraints and recommend "
            "a safe corrective action. No cluster changes are authorized."
        )

    target = _extract_target(normalized, resource)
    namespace = _extract_namespace(normalized)

    if resource == "pod" and target in {
        "scheduling",
        "is",
        "named",
        "in",
        "for",
    }:
        target = None

    if (
        not target
        or not namespace
        or not RESOURCE_NAME_PATTERN.fullmatch(target)
        or not RESOURCE_NAME_PATTERN.fullmatch(namespace)
    ):
        return {
            "action": action,
            "status": "needs_clarification",
            "resource_kind": resource.capitalize(),
            "resource_name": target,
            "deployment": target if resource == "deployment" else None,
            "namespace": namespace,
            "reason": (
                f"A valid {resource} name and namespace are required "
                "before a proposal can be prepared."
            ),
            "execution_enabled": False,
        }

    return {
        "action": action,
        "status": "proposed",
        "resource_kind": resource.capitalize(),
        "resource_name": target,
        "deployment": target if resource == "deployment" else None,
        "namespace": namespace,
        "reason": reason,
        "execution_enabled": False,
    }
