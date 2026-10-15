
"""Proposal-only Kubernetes remediation.

This module does not execute Kubernetes operations.
"""

import re
from typing import Any


SUPPORTED_ACTIONS = {
    "restart_deployment": "Restart a Kubernetes Deployment",
}

# Kubernetes resource names are lowercase DNS-style names.
RESOURCE_NAME_PATTERN = re.compile(
    r"^[a-z0-9](?:[-a-z0-9.]*[a-z0-9])?$"
)


def build_remediation_proposal(question: str) -> dict[str, Any] | None:
    """Return a proposal for an explicitly requested Deployment restart.

    This function only constructs a proposal. It never invokes Kubernetes,
    MCP tools, shell commands, or write operations.
    """
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

    if not restart_requested:
        return None

    
    deployment_match = re.search(
        r"\bdeployment(?:\s+named)?\s+([^\s]+)",
        normalized,
    )
    namespace_match = re.search(
        r"\bnamespace\s+([^\s]+)",
        normalized,
    )

    deployment = deployment_match.group(1) if deployment_match else None
    namespace = namespace_match.group(1) if namespace_match else None

    if (
        not deployment
        or not namespace
        or not RESOURCE_NAME_PATTERN.fullmatch(deployment)
        or not RESOURCE_NAME_PATTERN.fullmatch(namespace)
    ):
        return {
            "action": "restart_deployment",
            "status": "needs_clarification",
            "deployment": deployment,
            "namespace": namespace,
            "reason": (
                "A Deployment name and namespace are both required "
                "before a proposal can be prepared."
            ),
            "execution_enabled": False,
        }

    return {
        "action": "restart_deployment",
        "status": "proposed",
        "deployment": deployment,
        "namespace": namespace,
        "reason": "The user explicitly requested a Deployment restart.",
        "execution_enabled": False,
    }
