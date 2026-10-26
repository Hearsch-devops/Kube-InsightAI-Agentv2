
"""Read-only Kubernetes health recommendations."""

from typing import Any


def _finding(
    *,
    severity: str,
    category: str,
    resource_kind: str,
    name: str,
    namespace: str,
    observation: str,
    evidence: list[str],
    likely_causes: list[str],
    commands: list[str],
    recommended_actions: list[str],
) -> dict[str, Any]:
    return {
        "severity": severity,
        "category": category,
        "resource": {
            "kind": resource_kind,
            "name": name,
            "namespace": namespace,
        },
        "observation": observation,
        "evidence": evidence,
        "likely_causes": likely_causes,
        "recommended_actions": recommended_actions,
        "commands": commands,
        "remediation_mode": "read_only",
        "approval_required_for_changes": True,
    }


def build_recommendations(
    pods: list[dict[str, Any]],
    deployments: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Convert Kubernetes observations into deterministic findings."""

    findings: list[dict[str, Any]] = []

    # 1. Pod and container health
    for pod in pods:
        if pod.get("error"):
            continue

        name = pod.get("name", "unknown")
        namespace = pod.get("namespace", "default")
        status = pod.get("status", "Unknown")
        containers = pod.get("containers") or []

        evidence: list[str] = []
        causes: list[str] = []
        actions: list[str] = []
        commands: list[str] = []
        severity = "warning"

        if status == "Failed":
            severity = "critical"
            evidence.append(f"Pod phase is {status}.")
            causes.append(
                "A container terminated unsuccessfully or the pod failed."
            )
            actions.append(
                "Inspect pod events and container termination details."
            )

        elif status == "Pending":
            evidence.append("Pod phase is Pending.")
            causes.append(
                "Scheduling constraints, resource availability, "
                "or image setup may be preventing startup."
            )
            actions.append(
                "Inspect scheduling events, resource requests, "
                "and node capacity."
            )

        elif status not in ("Running", "Succeeded"):
            evidence.append(f"Pod phase is {status}.")
            causes.append(
                "The pod is not in a normal Running or Succeeded phase."
            )
            actions.append("Inspect the pod description and recent events.")

        for container in containers:
            container_name = container.get("name", "unknown")
            reason = container.get("reason")
            state = container.get("state")
            restart_count = container.get("restart_count", 0)
            last_state = container.get("last_state") or {}
            last_reason = last_state.get("reason")

            if reason == "CrashLoopBackOff":
                severity = "critical"
                evidence.append(
                    f"Container {container_name} is in CrashLoopBackOff."
                )
                causes.append(
                    "The application repeatedly exits or fails during startup."
                )
                actions.append(
                    f"Inspect current and previous logs for {container_name}."
                )

            elif reason == "ImagePullBackOff":
                severity = "critical"
                evidence.append(
                    f"Container {container_name} has ImagePullBackOff."
                )
                causes.append(
                    "The image may be unavailable or registry access "
                    "may be misconfigured."
                )
                actions.append(
                    "Verify the image name, tag, registry connectivity, "
                    "and image-pull credentials."
                )

            elif reason == "ErrImagePull":
                severity = "critical"
                evidence.append(
                    f"Container {container_name} has ErrImagePull."
                )
                causes.append(
                    "Kubernetes could not retrieve the configured image."
                )
                actions.append(
                    "Inspect the event message and verify the image reference."
                )

            elif reason == "OOMKilled" or last_reason == "OOMKilled":
                severity = "critical"
                evidence.append(
                    f"Container {container_name} was terminated by OOMKilled."
                )
                causes.append(
                    "The container exceeded its memory allowance "
                    "or encountered memory pressure."
                )
                actions.append(
                    "Inspect memory usage, limits, and previous container logs."
                )

            elif state == "waiting" and reason:
                evidence.append(
                    f"Container {container_name} is waiting: {reason}."
                )
                causes.append(
                    container.get("message")
                    or f"Container waiting reason: {reason}."
                )
                actions.append(
                    "Inspect pod events and container configuration."
                )

            if restart_count >= 3:
                severity = (
                    "critical" if restart_count >= 5 else severity
                )
                evidence.append(
                    f"Container {container_name} has restarted "
                    f"{restart_count} times."
                )
                actions.append(
                    "Review previous container logs and termination reasons."
                )

        if not pod.get("ready", False) and status == "Running":
            evidence.append("Pod Ready condition is not True.")
            causes.append(
                "A readiness probe may be failing or one or more "
                "containers may not be ready."
            )
            actions.append(
                "Inspect readiness probes and container readiness status."
            )

        # Only emit one combined finding for each pod.
        if evidence:
            commands = [
                f"kubectl describe pod {name} -n {namespace}",
                f"kubectl get events -n {namespace} "
                "--sort-by=.metadata.creationTimestamp",
            ]

            if any(
                c.get("restart_count", 0) > 0
                or c.get("last_state")
                for c in containers
            ):
                commands.append(
                    f"kubectl logs {name} -n {namespace} --previous"
                )

            findings.append(
                _finding(
                    severity=severity,
                    category="pod_health",
                    resource_kind="Pod",
                    name=name,
                    namespace=namespace,
                    observation=(
                        f"Pod {name} requires investigation."
                    ),
                    evidence=list(dict.fromkeys(evidence)),
                    likely_causes=list(dict.fromkeys(causes)),
                    commands=list(dict.fromkeys(commands)),
                    recommended_actions=list(dict.fromkeys(actions)),
                )
            )

    # 2. Deployment availability
    for deployment in deployments:
        if deployment.get("error"):
            continue

        name = deployment.get("name", "unknown")
        namespace = deployment.get("namespace", "default")
        desired = deployment.get("desired_replicas", 0) or 0
        ready = deployment.get("ready_replicas", 0) or 0
        available = deployment.get("available_replicas", 0) or 0

        if available >= desired and ready >= desired:
            continue

        findings.append(
            _finding(
                severity="critical" if available == 0 and desired > 0
                else "warning",
                category="deployment_availability",
                resource_kind="Deployment",
                name=name,
                namespace=namespace,
                observation=(
                    f"Deployment {name} has {available} available "
                    f"replica(s) out of {desired} desired."
                ),
                evidence=[
                    f"Desired replicas: {desired}",
                    f"Ready replicas: {ready}",
                    f"Available replicas: {available}",
                ],
                likely_causes=[
                    "Pods may be failing, pending scheduling, "
                    "or not passing readiness checks."
                ],
                recommended_actions=[
                    "Inspect deployment rollout status and associated pods.",
                    "Review pod events, image configuration, and readiness probes.",
                ],
                commands=[
                    f"kubectl describe deployment {name} -n {namespace}",
                    f"kubectl rollout status deployment/{name} -n {namespace}",
                    f"kubectl get pods -n {namespace}",
                ],
            )
        )

    # 3. Warning events
    for event in events:
        if event.get("error"):
            continue

        event_type = (event.get("type") or "").lower()
        if event_type != "warning":
            continue

        name = event.get("object") or event.get("name") or "unknown"
        namespace = event.get("namespace", "default")
        kind = event.get("object_kind") or "Resource"
        reason = event.get("reason") or "Warning"
        message = event.get("message") or "No event message available."

        findings.append(
            _finding(
                severity="warning",
                category="kubernetes_event",
                resource_kind=kind,
                name=name,
                namespace=namespace,
                observation=f"{reason}: {message}",
                evidence=[
                    f"Event reason: {reason}",
                    f"Event message: {message}",
                ],
                likely_causes=[
                    "The Kubernetes event indicates a condition "
                    "that may require investigation."
                ],
                recommended_actions=[
                    "Inspect the affected resource and its recent events."
                ],
                commands=[
                    f"kubectl describe {kind.lower()} {name} -n {namespace}",
                    f"kubectl get events -n {namespace} "
                    "--sort-by=.metadata.creationTimestamp",
                ],
            )
        )

    severity_order = {
        "critical": 0,
        "warning": 1,
        "info": 2,
    }

    findings.sort(
        key=lambda item: severity_order.get(item["severity"], 3)
    )

    return findings
