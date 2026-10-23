from mcp.server.mcpserver import MCPServer
from kubernetes import client, config

from datetime import datetime

import os

from pathlib import Path


server = MCPServer("Kube-InsightAI Kubernetes Server")


def get_kubernetes_client():

    config.load_incluster_config()

    return client.CoreV1Api()

# get_cluster_metrics
@server.tool()
def get_cluster_metrics() -> dict:
    try:
        v1 = get_kubernetes_client()
        nodes = v1.list_node()

        total_nodes = len(nodes.items)
        ready_nodes = 0
        not_ready_nodes = 0

        total_cpu_capacity = 0
        total_cpu_allocatable = 0
        total_memory_capacity = 0
        total_memory_allocatable = 0

        node_details = []

        for node in nodes.items:
            node_name = node.metadata.name

            capacity = node.status.capacity or {}
            allocatable = node.status.allocatable or {}

            cpu_capacity = capacity.get("cpu", "0")
            cpu_allocatable = allocatable.get("cpu", "0")

            memory_capacity = capacity.get("memory", "0")
            memory_allocatable = allocatable.get("memory", "0")

            total_cpu_capacity += int(cpu_capacity)
            total_cpu_allocatable += int(cpu_allocatable)

            total_memory_capacity += int(
                memory_capacity.replace("Ki", "")
            )
            total_memory_allocatable += int(
                memory_allocatable.replace("Ki", "")
            )

            ready = False

            for condition in node.status.conditions or []:
                if condition.type == "Ready":
                    ready = condition.status == "True"
                    break

            if ready:
                ready_nodes += 1
            else:
                not_ready_nodes += 1

            node_details.append({
                "name": node_name,
                "ready": ready,
                "cpu_capacity": cpu_capacity,
                "cpu_allocatable": cpu_allocatable,
                "memory_capacity": memory_capacity,
                "memory_allocatable": memory_allocatable,
            })

        return {
            "nodes": {
                "total": total_nodes,
                "ready": ready_nodes,
                "not_ready": not_ready_nodes,
            },
            "resources": {
                "cpu": {
                    "capacity": f"{total_cpu_capacity}",
                    "allocatable": f"{total_cpu_allocatable}",
                },
                "memory": {
                    "capacity": f"{total_memory_capacity}Ki",
                    "allocatable": f"{total_memory_allocatable}Ki",
                },
            },
            "node_details": node_details,
        }

    except Exception as exc:
        return {
            "error": f"Kubernetes MCP error: {type(exc).__name__}: {exc}"
        }

# list_pods
@server.tool()
def list_pods(namespace: str | None = None) -> list[dict]:
    try:
        v1 = get_kubernetes_client()

        if namespace:
            pods = v1.list_namespaced_pod(namespace)
        else:
            pods = v1.list_pod_for_all_namespaces()

        results = []

        for pod in pods.items:
            ready = False

            if pod.status and pod.status.conditions:
                for condition in pod.status.conditions:
                    if condition.type == "Ready":
                        ready = condition.status == "True"
                        break

            ready_containers = 0
            total_containers = 0
            container_details = []

            if pod.status and pod.status.container_statuses:
                total_containers = len(pod.status.container_statuses)

                ready_containers = sum(
                    1
                    for container in pod.status.container_statuses
                    if container.ready
                )

                for container in pod.status.container_statuses:
                    state = "unknown"
                    reason = None
                    message = None
                    exit_code = None
                    signal = None

                    if container.state:
                        if container.state.waiting:
                            state = "waiting"
                            reason = container.state.waiting.reason
                            message = container.state.waiting.message

                        elif container.state.running:
                            state = "running"

                        elif container.state.terminated:
                            state = "terminated"
                            reason = container.state.terminated.reason
                            message = container.state.terminated.message
                            exit_code = container.state.terminated.exit_code
                            signal = container.state.terminated.signal

                    # Capture the previous container termination, if available.
                    last_state = None
                    if container.last_state and container.last_state.terminated:
                        terminated = container.last_state.terminated
                        last_state = {
                            "reason": terminated.reason,
                            "message": terminated.message,
                            "exit_code": terminated.exit_code,
                            "signal": terminated.signal,
                            "started_at": (
                                terminated.started_at.isoformat()
                                if terminated.started_at else None
                            ),
                            "finished_at": (
                                terminated.finished_at.isoformat()
                                if terminated.finished_at else None
                            ),
                        }

                    # Match the container status to its configured specification.
                    container_spec = next(
                        (
                            spec
                            for spec in (pod.spec.containers or [])
                            if spec.name == container.name
                        ),
                        None,
                    )

                    container_details.append({
                        "name": container.name,
                        "image": container_spec.image if container_spec else None,
                        "command": (
                            container_spec.command or []
                            if container_spec else []
                        ),
                        "args": (
                            container_spec.args or []
                            if container_spec else []
                        ),
                        "ready": container.ready,
                        "restart_count": container.restart_count,
                        "state": state,
                        "reason": reason,
                        "message": message,
                        "exit_code": exit_code,
                        "signal": signal,
                        "last_state": last_state,
                    })

            results.append({
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "status": (
                    pod.status.phase
                    if pod.status
                    else "Unknown"
                ),
                "ready": ready,
                "ready_containers": ready_containers,
                "total_containers": total_containers,
                "node": (
                    pod.spec.node_name
                    if pod.spec
                    else None
                ),
                "containers": container_details,
            })

        return results

    except Exception as exc:
        return [{
            "error": (
                f"Kubernetes MCP error: "
                f"{type(exc).__name__}: {exc}"
            )
        }]

@server.tool()
def get_pod_owner(
    pod_name: str,
    namespace: str = "default",
) -> dict:
    """
    Return the Kubernetes ownership chain for a Pod.

    Identifies whether the Pod is standalone or managed by
    a ReplicaSet/Deployment.
    """
    try:
        v1 = get_kubernetes_client()

        pod = v1.read_namespaced_pod(
            name=pod_name,
            namespace=namespace,
        )

        owner_references = pod.metadata.owner_references or []

        # ---------------------------------------------------------
        # Standalone Pod
        # ---------------------------------------------------------
        if not owner_references:
            return {
                "pod": pod_name,
                "namespace": namespace,
                "owner": None,
                "owner_kind": None,
                "owner_name": None,
                "deployment": None,
                "deployment_name": None,
                "standalone": True,
            }

        owner = owner_references[0]

        result = {
            "pod": pod_name,
            "namespace": namespace,
            "owner": owner.name,
            "owner_kind": owner.kind,
            "owner_name": owner.name,
            "deployment": None,
            "deployment_name": None,
            "standalone": False,
        }

        # ---------------------------------------------------------
        # ReplicaSet → Deployment
        # ---------------------------------------------------------
        if owner.kind == "ReplicaSet":
            apps_v1 = client.AppsV1Api()

            replica_set = apps_v1.read_namespaced_replica_set(
                name=owner.name,
                namespace=namespace,
            )

            rs_owner_references = (
                replica_set.metadata.owner_references or []
            )

            for rs_owner in rs_owner_references:
                if rs_owner.kind == "Deployment":
                    result["deployment"] = rs_owner.name
                    result["deployment_name"] = rs_owner.name
                    break

        return result

    except Exception as exc:
        return {
            "error": (
                f"Kubernetes MCP error: "
                f"{type(exc).__name__}: {exc}"
            )
        }

# get_pod_logs
@server.tool()
def get_pod_logs(
    pod_name: str,
    namespace: str = "default",
    container: str | None = None,
    tail_lines: int = 100,
) -> str:
    """
    Retrieve logs from a Kubernetes pod.

    Args:
        pod_name: Name of the Kubernetes pod.
        namespace: Kubernetes namespace.
        container: Optional container name.
        tail_lines: Number of recent log lines to retrieve.
    """

    try:
        v1 = get_kubernetes_client()

        since_time = None

        logs = v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            container=container,
            tail_lines=tail_lines,
        )

        if not logs:
            return f"No logs found for pod '{pod_name}'."

        if isinstance(logs, bytes):
            logs = logs.decode(
                "utf-8",
                errors="replace"
            )

        elif (
            isinstance(logs, str)
            and logs.startswith("b'")
            and logs.endswith("'")
        ):
            logs = (
                logs[2:-1]
                .encode("utf-8")
                .decode("unicode_escape")
            )

        return (
                        f"Pod: {pod_name}\n"
                        f"Namespace: {namespace}\n"
                        f"Container: {container or 'default'}\n\n"
                        f"Logs:\n{logs}"
                )

    except Exception as exc:
        return (
            f"Kubernetes MCP error: "
            f"{type(exc).__name__}: {exc}"
        )

# get_pod_logs_by_time
@server.tool()
def get_pod_logs_by_time(
    pod_name: str,
    namespace: str = "default",
    start_time: str | None = None,
    end_time: str | None = None,
    container: str | None = None,
) -> str:
    """
    Retrieve Kubernetes pod logs within a specific time range.

    start_time and end_time must be ISO-8601 timestamps.
    Example:
        2026-10-02T10:00:00
    """

    try:
        v1 = get_kubernetes_client()

        logs = v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            container=container,
            timestamps=True,
        )

        if not logs:
            return f"No logs found for pod '{pod_name}'."

        if isinstance(logs, bytes):
            logs = logs.decode("utf-8", errors="replace")

        elif (
            isinstance(logs, str)
            and logs.startswith("b'")
            and logs.endswith("'")
        ):
            logs = (
                logs[2:-1]
                .encode("utf-8")
                .decode("unicode_escape")
            )

        lines = logs.splitlines()

        filtered_lines = []

        start_dt = (
            datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            if start_time
            else None
        )

        end_dt = (
            datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            if end_time
            else None
        )

        filtered_lines = []

        for line in lines:
            try:
                timestamp_text = line.split(" ", 1)[0]

                log_dt = datetime.fromisoformat(
                    timestamp_text.replace("Z", "+00:00")
                )

                if start_dt and log_dt < start_dt:
                    continue

                if end_dt and log_dt > end_dt:
                    continue

                filtered_lines.append(line)

            except (ValueError, IndexError):
                continue

        if not filtered_lines:
            return (
                f"No logs found for pod '{pod_name}' "
                f"within the requested time range."
            )

        return (
            f"Pod: {pod_name}\n"
            f"Namespace: {namespace}\n"
            f"Container: {container or 'default'}\n"
            f"Start: {start_time or 'beginning'}\n"
            f"End: {end_time or 'now'}\n\n"
            f"Logs:\n"
            + "\n".join(filtered_lines)
        )

    except Exception as exc:
        return (
            f"Kubernetes MCP error: "
            f"{type(exc).__name__}: {exc}"
        )

# list_deployments
@server.tool()
def list_deployments(namespace: str | None = None) -> list[dict]:
    try:
        config.load_incluster_config()
        apps_v1 = client.AppsV1Api()

        if namespace:
            deployments = apps_v1.list_namespaced_deployment(namespace)
        else:
            deployments = apps_v1.list_deployment_for_all_namespaces()

        results = []

        for deployment in deployments.items:
            results.append({
                "name": deployment.metadata.name,
                "namespace": deployment.metadata.namespace,
                "desired_replicas": deployment.spec.replicas or 0,
                "ready_replicas": deployment.status.ready_replicas or 0,
                "available_replicas": deployment.status.available_replicas or 0,
            })

        return results

    except Exception as exc:
        return [{
            "error": f"Kubernetes MCP error: {type(exc).__name__}: {exc}"
        }]

#event_timestamp
def get_event_timestamp(event):
    """
    Return the most reliable timestamp available for a Kubernetes event.
    """

    if event.event_time:
        return event.event_time

    if event.series and event.series.last_observed_time:
        return event.series.last_observed_time

    if event.last_timestamp:
        return event.last_timestamp

    if event.first_timestamp:
        return event.first_timestamp

    return None

# list_events_by_time
@server.tool()
def list_events_by_time(
    namespace: str | None,
    start_time: str,
    end_time: str,
) -> list[dict]:
    try:
        v1 = get_kubernetes_client()

        start_dt = datetime.fromisoformat(
            start_time.replace("Z", "+00:00")
        )
        end_dt = datetime.fromisoformat(
            end_time.replace("Z", "+00:00")
        )

        if namespace:
            events = v1.list_namespaced_event(namespace)
        else:
            events = v1.list_event_for_all_namespaces()

        results = []

        for event in events.items:
            event_timestamp = get_event_timestamp(event)

            if not event_timestamp:
                continue

            # Make sure both timestamps are timezone-aware.
            if event_timestamp.tzinfo is None:
                event_timestamp = event_timestamp.replace(
                    tzinfo=start_dt.tzinfo
                )

            if start_dt <= event_timestamp <= end_dt:
                results.append({
                    "timestamp": event_timestamp.isoformat(),
                    "name": event.metadata.name,
                    "namespace": event.metadata.namespace,
                    "type": event.type,
                    "reason": event.reason,
                    "message": event.message,
                    "object": (
                        event.involved_object.name
                        if event.involved_object
                        else None
                    ),
                    "object_kind": (
                        event.involved_object.kind
                        if event.involved_object
                        else None
                    ),
                    "count": event.count,
                    "first_timestamp": (
                        event.first_timestamp.isoformat()
                        if event.first_timestamp
                        else None
                    ),
                    "last_timestamp": (
                        event.last_timestamp.isoformat()
                        if event.last_timestamp
                        else None
                    ),
                })

        # Return events chronologically.
        results.sort(
            key=lambda event: event["timestamp"]
        )

        return results

    except Exception as exc:
        return [{
            "error": f"Kubernetes MCP error: {type(exc).__name__}: {exc}"
        }]

# list_events
@server.tool()
def list_events(namespace: str | None = None) -> list[dict]:
    try:
        v1 = get_kubernetes_client()

        if namespace:
            events = v1.list_namespaced_event(namespace)
        else:
            events = v1.list_event_for_all_namespaces()

        results = []

        for event in events.items:
            event_timestamp = get_event_timestamp(event)

            results.append({
                "name": event.metadata.name,
                "namespace": event.metadata.namespace,
                "type": event.type,
                "reason": event.reason,
                "message": event.message,
                "object": (
                    event.involved_object.name
                    if event.involved_object
                    else None
                ),
                "object_kind": (
                    event.involved_object.kind
                    if event.involved_object
                    else None
                ),
                "count": event.count,
                "timestamp": (
                    event_timestamp.isoformat()
                    if event_timestamp
                    else None
                ),
                "first_timestamp": (
                    event.first_timestamp.isoformat()
                    if event.first_timestamp
                    else None
                ),
                "last_timestamp": (
                    event.last_timestamp.isoformat()
                    if event.last_timestamp
                    else None
                ),
            })

        # Return events chronologically by event timestamp.
        results.sort(
            key=lambda event: event["timestamp"] or ""
        )

        return results

    except Exception as exc:
        return [{
            "error": f"Kubernetes MCP error: {type(exc).__name__}: {exc}"
        }]

# get_pod_events
@server.tool()
def get_pod_events(
    pod_name: str,
    namespace: str = "default",
) -> list[dict]:
    try:
        v1 = get_kubernetes_client()

        events = v1.list_namespaced_event(namespace)

        results = []

        for event in events.items:

            if (
                not event.involved_object
                or event.involved_object.kind != "Pod"
                or event.involved_object.name != pod_name
            ):
                continue

            results.append({
                "name": event.metadata.name,
                "namespace": event.metadata.namespace,
                "type": event.type,
                "reason": event.reason,
                "message": event.message,
                "object": event.involved_object.name,
                "object_kind": event.involved_object.kind,
                "count": event.count,
                "first_timestamp": (
                    event.first_timestamp.isoformat()
                    if event.first_timestamp
                    else None
                ),
                "last_timestamp": (
                    event.last_timestamp.isoformat()
                    if event.last_timestamp
                    else None
                ),
            })

        if not results:
            return [{
                "message": (
                    f"No events found for pod "
                    f"'{pod_name}' in namespace '{namespace}'."
                )
            }]

        # Return pod events chronologically by their latest occurrence.
        results.sort(
            key=lambda event: (
                event["last_timestamp"]
                or event["first_timestamp"]
                or ""
            )
        )

        return results

    except Exception as exc:
        return [{
            "error": (
                f"Kubernetes MCP error: "
                f"{type(exc).__name__}: {exc}"
            )
        }]

# list_services
@server.tool()
def list_services(namespace: str | None = None) -> list[dict]:
    try:
        v1 = get_kubernetes_client()

        if namespace:
            services = v1.list_namespaced_service(namespace)
        else:
            services = v1.list_service_for_all_namespaces()

        results = []

        for service in services.items:
            ports = []

            if service.spec and service.spec.ports:
                for port in service.spec.ports:
                    ports.append({
                        "port": port.port,
                        "target_port": str(port.target_port),
                        "protocol": port.protocol,
                    })

            results.append({
                "name": service.metadata.name,
                "namespace": service.metadata.namespace,
                "type": service.spec.type if service.spec else "Unknown",
                "cluster_ip": service.spec.cluster_ip if service.spec else None,
                "ports": ports,
            })

        return results

    except Exception as exc:
        return [{
            "error": f"Kubernetes MCP error: {type(exc).__name__}: {exc}"
        }]

# list_ingresses
@server.tool()
def list_ingresses(namespace: str | None = None) -> list[dict]:
    try:
        config.load_incluster_config()
        networking_v1 = client.NetworkingV1Api()

        if namespace:
            ingresses = networking_v1.list_namespaced_ingress(namespace)
        else:
            ingresses = networking_v1.list_ingress_for_all_namespaces()

        results = []

        for ingress in ingresses.items:
            hosts = []

            if ingress.spec and ingress.spec.rules:
                for rule in ingress.spec.rules:
                    if rule.host:
                        hosts.append(rule.host)

            addresses = []

            if ingress.status and ingress.status.load_balancer:
                for address in ingress.status.load_balancer.ingress or []:
                    if address.ip:
                        addresses.append(address.ip)
                    elif address.hostname:
                        addresses.append(address.hostname)

            ingress_class = None

            if ingress.spec:
                ingress_class = ingress.spec.ingress_class_name

            results.append({
                "name": ingress.metadata.name,
                "namespace": ingress.metadata.namespace,
                "class": ingress_class,
                "hosts": hosts,
                "addresses": addresses,
            })

        return results

    except Exception as exc:
        return [{
            "error": f"Kubernetes MCP error: {type(exc).__name__}: {exc}"
        }]

# list_namespaces
@server.tool()
def list_namespaces() -> list[dict]:
    """
    List all Kubernetes namespaces.
    """
    try:
        v1 = get_kubernetes_client()

        namespaces = v1.list_namespace()

        if not namespaces.items:
            return []

        results = []

        for namespace in namespaces.items:
            name = namespace.metadata.name

            status = (
                namespace.status.phase
                if namespace.status
                else "Unknown"
            )

            results.append({
                "name": name,
                "status": status,
            })

        return results

    except Exception as exc:
        return [
            {
                "error": (
                    f"Kubernetes MCP error: "
                    f"{type(exc).__name__}: {exc}"
                )
            }
        ]
# get_pod_scheduling_details
@server.tool()
def get_pod_scheduling_details(
    pod_name: str,
    namespace: str = "default",
) -> dict:
    """Return read-only scheduling configuration for a pod."""
    try:
        v1 = get_kubernetes_client()
        pod = v1.read_namespaced_pod(
            name=pod_name,
            namespace=namespace,
        )

        spec = pod.spec
        affinity = spec.affinity

        node_affinity = None
        if affinity and affinity.node_affinity:
            node_affinity = affinity.node_affinity.to_dict()

        return {
            "pod": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "phase": pod.status.phase if pod.status else "Unknown",
            "node_name": spec.node_name,
            "node_selector": spec.node_selector or {},
            "node_affinity": node_affinity,
            "tolerations": [
                item.to_dict()
                for item in (spec.tolerations or [])
            ],
        }

    except Exception as exc:
        return {
            "error": (
                f"Kubernetes MCP error: "
                f"{type(exc).__name__}: {exc}"
            )
        }

# get_node_scheduling_details
@server.tool()
def get_node_scheduling_details() -> list[dict]:
    """Return read-only labels, taints, and readiness for cluster nodes."""
    try:
        v1 = get_kubernetes_client()
        nodes = v1.list_node()
        results = []

        for node in nodes.items:
            ready = False
            for condition in (node.status.conditions or []):
                if condition.type == "Ready":
                    ready = condition.status == "True"
                    break

            results.append({
                "name": node.metadata.name,
                "ready": ready,
                "labels": node.metadata.labels or {},
                "taints": [
                    taint.to_dict()
                    for taint in (node.spec.taints or [])
                ],
            })

        return results

    except Exception as exc:
        return [{
            "error": (
                f"Kubernetes MCP error: "
                f"{type(exc).__name__}: {exc}"
            )
        }]

if __name__ == "__main__":
    server.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8001,
    )