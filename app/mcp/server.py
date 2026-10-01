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

            if pod.status and pod.status.container_statuses:
                total_containers = len(pod.status.container_statuses)

                ready_containers = sum(
                    1
                    for container in pod.status.container_statuses
                    if container.ready
                )

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
            })

        return results

    except Exception as exc:
        return [{
            "error": (
                f"Kubernetes MCP error: "
                f"{type(exc).__name__}: {exc}"
            )
        }]

# get_pod_logs
@server.tool()
def get_pod_logs(
    pod_name: str,
    namespace: str = "default",
    container: str | None = None,
    tail_lines: int = 100,
    start_time: str | None = None,
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

        if start_time:
            since_time = datetime.fromisoformat(
                start_time.replace("Z", "+00:00")
            )

        logs = v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=namespace,
            container=container,
            tail_lines=tail_lines,
            since_time=since_time,
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

        return results

    except Exception as exc:
        return [{
            "error": f"Kubernetes MCP error: {type(exc).__name__}: {exc}"
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

if __name__ == "__main__":
    server.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8001,
    )