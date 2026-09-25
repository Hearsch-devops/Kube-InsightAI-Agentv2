from mcp.server.mcpserver import MCPServer
from kubernetes import client, config
import os

from pathlib import Path


server = MCPServer("Kube-InsightAI Kubernetes Server")


def get_kubernetes_client():

    config.load_incluster_config()

    return client.CoreV1Api()


# list_pods
@server.tool()
def list_pods(namespace: str = "default") -> str:
    """
    List Kubernetes pods in a namespace.

    Args:
        namespace: Kubernetes namespace to inspect.
    """

    try:
        v1 = get_kubernetes_client()

        pods = v1.list_namespaced_pod(
            namespace=namespace
        )

        if not pods.items:
            return f"No pods found in namespace '{namespace}'."

        results = []

        for pod in pods.items:
            results.append(
                f"Pod: {pod.metadata.name}\n"
                f"Status: {pod.status.phase}\n"
            )

        return "\n".join(results)

    except Exception as exc:
        return (
            f"Kubernetes MCP error: "
            f"{type(exc).__name__}: {exc}"
        )

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

# list_deployments
@server.tool()
def list_deployments(namespace: str = "default") -> str:
    """
    List Kubernetes deployments in a namespace.

    Args:
        namespace: Kubernetes namespace to inspect.
    """

    try:
        config.load_kube_config(
            config_file=os.path.expanduser("~/.kube/config")
        )

        apps_v1 = client.AppsV1Api()

        deployments = apps_v1.list_namespaced_deployment(
            namespace=namespace
        )

        if not deployments.items:
            return (
                f"No deployments found in namespace "
                f"'{namespace}'."
            )

        results = []

        for deployment in deployments.items:
            name = deployment.metadata.name
            desired = deployment.spec.replicas or 0
            ready = deployment.status.ready_replicas or 0
            available = deployment.status.available_replicas or 0

            results.append(
                f"Deployment: {name}\n"
                f"Desired Replicas: {desired}\n"
                f"Ready Replicas: {ready}\n"
                f"Available Replicas: {available}\n"
            )

        return "\n".join(results)

    except Exception as exc:
        return (
            f"Kubernetes MCP error: "
            f"{type(exc).__name__}: {exc}"
        )
# list_events
@server.tool()
def list_events(namespace: str = "default", limit: int = 50) -> str:
    """
    List recent Kubernetes events in a namespace.

    Args:
        namespace: Kubernetes namespace to inspect.
        limit: Maximum number of events to return.
    """

    try:
        v1 = get_kubernetes_client()

        events = v1.list_namespaced_event(
            namespace=namespace
        )

        if not events.items:
            return (
                f"No events found in namespace "
                f"'{namespace}'."
            )

        sorted_events = sorted(
            events.items,
            key=lambda event: (
                event.last_timestamp
                or event.event_time
                or event.first_timestamp
            ),
            reverse=True,
        )

        results = []

        for event in sorted_events[:limit]:
            reason = event.reason or "Unknown"
            event_type = event.type or "Normal"
            message = event.message or "No message"

            involved_object = event.involved_object

            object_name = (
                involved_object.name
                if involved_object
                else "Unknown"
            )

            object_kind = (
                involved_object.kind
                if involved_object
                else "Unknown"
            )

            results.append(
                f"Type: {event_type}\n"
                f"Reason: {reason}\n"
                f"Object: {object_kind}/{object_name}\n"
                f"Message: {message}\n"
            )

        return "\n".join(results)

    except Exception as exc:
        return (
            f"Kubernetes MCP error: "
            f"{type(exc).__name__}: {exc}"
        )

# list_services
@server.tool()
def list_services(namespace: str = "default") -> str:
    """
    List Kubernetes services in a namespace.

    Args:
        namespace: Kubernetes namespace to inspect.
    """

    try:
        v1 = get_kubernetes_client()

        services = v1.list_namespaced_service(
            namespace=namespace
        )

        if not services.items:
            return (
                f"No services found in namespace "
                f"'{namespace}'."
            )

        results = []

        for service in services.items:
            service_name = service.metadata.name
            service_type = service.spec.type
            cluster_ip = service.spec.cluster_ip

            ports = []

            if service.spec.ports:
                for port in service.spec.ports:
                    ports.append(
                        f"{port.port}/{port.protocol}"
                    )

            results.append(
                f"Service: {service_name}\n"
                f"Type: {service_type}\n"
                f"ClusterIP: {cluster_ip}\n"
                f"Ports: {', '.join(ports) if ports else 'None'}\n"
            )

        return "\n".join(results)

    except Exception as exc:
        return (
            f"Kubernetes MCP error: "
            f"{type(exc).__name__}: {exc}"
        )

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