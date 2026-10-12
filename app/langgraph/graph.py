from app.mcp_client import (
    call_mcp_tool,
    parse_mcp_result,
    KUBERNETES_MCP_URL,
)
import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Literal
import json
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph

from app.langgraph.state import AgentState
from app.llm.llm import get_chat_model


from lc_demos.langchain_retriever_demo import retriever
from lc_demos.langchain_rag_chain import format_documents


logger = logging.getLogger(__name__)

MCP_KEYWORDS = (
    "pod",
    "pods",
    "running",
    "status",
    "health",
    "healthy",
    "ready",
    "readiness",
    "liveness",
    "alive",
    "available",
    "availability",
    "uptime",
    "deployment",
    "deployments",
    "service",
    "services",
    "event",
    "events",
    "logs",
    "log",
)

KUBERNETES_KEYWORDS = (
    "kubernetes",
    "k8s",
    "kubectl",
    "namespace",
    "configmap",
    "secret",
    "ingress",
    "helm",
    "container",
    "node",
)

LIVE_CLUSTER_KEYWORDS = (
    "running pods",
    "what pods are running",
    "what pods are currently running",
    "which pods are currently running",
    "pods currently running",
    "pod status",
    "pod logs",
    "logs of",
    "deployment status",
    "deployment health",
    "running deployments",
    "cluster events",
    "kubernetes events",
    "events in",
    "what is running",
    "which pods",
    "which deployments",

    # Services — only live-cluster intent
    "service status",
    "running services",
    "which services",
    "services running",
    "services currently running",
    "what services are available",
)

INVESTIGATION_KEYWORDS = (
    "investigate",
    "troubleshoot",
    "why is",
    "why did",
    "what went wrong",
    "what is wrong",
    "why",
    "crash",
    "crashed",
    "crashing",
    "restart",
    "restarted",
    "restarting",
    "failed",
    "failure",
    "failing",
    "error",
    "issue",
    "problem",
    "root cause",
    "what caused",
    "abnormal behavior",
    "abnormal",
    "unhealthy",
    "not healthy",
    "unexpected behavior",
    "historical events",
    "history of events",
    "recent events",
    "current health",
    "health of",
)

def extract_question(state: AgentState) -> str:
    """Extract the latest user question from the graph state."""

    if state.get("question"):
        return str(state["question"])

    for message in reversed(state.get("messages", [])):
        if isinstance(message, HumanMessage):
            return str(message.content)

    raise ValueError("No user question found in graph state")


async def analyze_question(state: AgentState) -> dict:
    """Analyze the user's question using the configured LLM."""

    question = extract_question(state)
    llm = get_chat_model()

    prompt = f"""
Analyze the following user question in one short, useful sentence.

Question:
{question}
"""

    try:
        response = await llm.ainvoke(prompt)

        return {
            "question": question,
            "analysis": str(response.content),
        }

    except Exception:
        logger.exception("Question analysis failed")

        return {
            "question": question,
            "analysis": "",
            "error": "Unable to analyze the question.",
        }

async def retrieve_context(state: AgentState) -> dict:
    """Retrieve relevant Kubernetes SOP content from the vector database."""

    question = extract_question(state)

    try:
        logger.info("Retrieving RAG context for question")

        documents = await asyncio.to_thread(
            retriever.invoke,
            question,
        )

        context = format_documents(documents)

        sources = [
            doc.metadata.get("source", "unknown")
            for doc in documents
        ]

        logger.info(
            "Retrieved %d documents from the knowledge base",
            len(documents),
        )

        return {
            "context": context,
            "sources": sources,
        }

    except Exception:
        logger.exception("RAG context retrieval failed")

        return {
            "context": "",
            "sources": [],
            "error": "Unable to retrieve information from the knowledge base.",
        }

def route_question(state: AgentState) -> dict:
    """Route the question to the appropriate response workflow."""

    question = extract_question(state).lower()

    logger.info("ROUTER QUESTION RECEIVED: %r", question)

    investigation_intent = (
        any(
            keyword in question
            for keyword in INVESTIGATION_KEYWORDS
        )
        and any(
            keyword in question
            for keyword in (
                "pod",
                "pods",
                "deployment",
                "container",
                "kubernetes",
                "k8s",
                "abnormal behavior",
                "abnormal",
                "unhealthy",
                "not healthy",
                "unexpected behavior",
                "historical events",
                "history of events",
                "recent events",
                "current health",
                "health of",
                "readiness",
                "readiness failure",
                "readiness probe",
                "unschedulable",
                "imagepullbackoff",
                "errimagepull",
                "crashloopbackoff",
                "root cause",
                "investigate",
                "troubleshoot",
                "diagnose",
            )
        )
    )

    ownership_intent = (
        any(
            keyword in question
            for keyword in (
                "who owns",
                "owner",
                "managed by",
                "controlled by",
            )
        )
        and (
            any(
                keyword in question
                for keyword in (
                    "pod",
                    "pods",
                )
            )
            or "namespace" in question
        )
    )

    live_cluster_intent = (
        any(
            keyword in question
            for keyword in LIVE_CLUSTER_KEYWORDS
        )

        or (
            "pod" in question
            and (
                "ready" in question
                or "readiness" in question
                or "healthy" in question
                or "health" in question
            )
        )

        or (
            "deployment" in question
            and (
                "running" in question
                or "status" in question
                or "health" in question
                or "healthy" in question
                or "ready" in question
                or "readiness" in question
            )
        )

        or (
            "agent" in question
            and (
                "health" in question
                or "healthy" in question
                or "ready" in question
                or "alive" in question
                or "status" in question
            )
        )

        or (
            "event" in question
            and (
                "cluster" in question
                or "kubernetes" in question
                or "namespace" in question
            )
        )

        or "show me the logs" in question
        or "get the logs" in question
    )

    if investigation_intent or ownership_intent:
        route: Literal["mcp", "kubernetes", "general"] = "mcp"

    elif live_cluster_intent:
        route = "mcp"

    elif any(
        keyword in question
        for keyword in KUBERNETES_KEYWORDS
    ):
        route = "kubernetes"

    else:
        route = "general"

    logger.info(
        "Intent detection: investigation=%s ownership=%s",
        investigation_intent,
        ownership_intent,
    )
    logger.info("Question routed to: %s", route)

    return {
        "route": route,
        "investigation_intent": investigation_intent,
        "ownership_intent": ownership_intent,
    }


def extract_log_time_range(question: str) -> tuple[str | None, str | None]:
    """
    Extract start and end timestamps from a log/event request.

    Supported formats:
        2026-10-02T09:12:00+00:00
        2026-10-02T09:14:00+00:00

        09:00 to 10:00
        09:00-10:00
        from 09:00 to 10:00

    Time-only ranges are interpreted using today's UTC date.
    """

    # ---------------------------------------------------------
    # Full ISO-8601 timestamps
    # ---------------------------------------------------------
    timestamps = re.findall(
        r"\d{4}-\d{2}-\d{2}T"
        r"\d{2}:\d{2}:\d{2}"
        r"(?:\.\d+)?"
        r"(?:Z|[+-]\d{2}:\d{2})",
        question,
    )

    if len(timestamps) >= 2:
        return timestamps[0], timestamps[1]

    # ---------------------------------------------------------
    # Time-only range
    # Example:
    #   09:00 to 10:00
    #   09:00-10:00
    #   from 09:00 to 10:00
    # ---------------------------------------------------------
    time_range = re.search(
        r"\b(?:from\s+)?"
        r"(\d{1,2}):(\d{2})"
        r"\s*(?:to|-)\s*"
        r"(\d{1,2}):(\d{2})\b",
        question.lower(),
    )

    if time_range:
        start_hour, start_minute, end_hour, end_minute = map(
            int,
            time_range.groups(),
        )

        now_utc = datetime.now(timezone.utc)
        today = now_utc.date()

        start_dt = datetime(
            today.year,
            today.month,
            today.day,
            start_hour,
            start_minute,
            tzinfo=timezone.utc,
        )

        end_dt = datetime(
            today.year,
            today.month,
            today.day,
            end_hour,
            end_minute,
            tzinfo=timezone.utc,
        )

        return (
            start_dt.isoformat(),
            end_dt.isoformat(),
        )

    return None, None

async def mcp_response(state: AgentState) -> dict:
    """Retrieve live Kubernetes information using MCP."""

    question = extract_question(state)
    question_lower = question.lower()

    investigation_intent = state.get("investigation_intent", False)
    ownership_intent = state.get("ownership_intent", False)

    requested_pod = None

    try:
        logger.info("Connecting to Kubernetes MCP server")

        # =========================================================
        # Resolve namespace for pod investigation/log request
        # =========================================================

        namespace_match = re.search(
            r"\bnamespace\s+([a-z0-9](?:[a-z0-9-]*[a-z0-9])?)\b",
            question_lower,
        )

        if namespace_match:
            requested_namespace = namespace_match.group(1)

        else:
            requested_namespace = "kube-insightaiv2"

        logger.info(
            "Requested namespace: %s",
            requested_namespace,
        )

        # =========================================================
        # Select the MCP tool based on the user's Kubernetes intent
        # =========================================================

        # ---------------------------------------------------------
        # Pod logs
        # ---------------------------------------------------------
        if investigation_intent or ownership_intent or any(
            keyword in question_lower
            for keyword in (
                "log",
                "logs",
                "logging",
            )
        ):
            logger.info("MCP log request detected")

            # First retrieve the current pod list from the requested namespace.
            pod_result = await call_mcp_tool(
                KUBERNETES_MCP_URL,
                "list_pods",
                {
                    "namespace": requested_namespace,
                },
            )

            if pod_result.is_error:
                raise RuntimeError(
                    f"Unable to list pods before retrieving logs: {pod_result}"
                )

            pod_context = (
                pod_result.structured_content.get("result", [])
                if pod_result.structured_content
                else []
            )

            logger.info(
                "PODS RETURNED FROM NAMESPACE %s: %s",
                requested_namespace,
                json.dumps(pod_context, indent=2),
            )

            logger.info(
                "NUMBER OF PODS RETURNED BY MCP: %d",
                len(pod_context),
            )

            logger.info(
                "AVAILABLE POD NAMES: %s",
                [
                    pod.get("name")
                    for pod in pod_context
                    if isinstance(pod, dict)
                ],
            )
            # =========================================================
            # Resolve requested pod or logical component
            # =========================================================

            component = None

            # Ownership questions may provide the pod name directly
            # without investigation keywords such as crashing/logs/events.
            ownership_pod_match = re.search(
                r"\bwho\s+owns\s+(?:pod\s+)?([a-z0-9][a-z0-9.-]*)\b",
                question_lower,
            )

            if ownership_pod_match:
                candidate_pod = ownership_pod_match.group(1)

                if candidate_pod not in {
                    "agent",
                    "mcp",
                    "frontend",
                    "pod",
                    "pods",
                }:
                    requested_pod = candidate_pod

            logger.info(
                "Ownership pod candidate: %s",
                requested_pod,
            )

            # First check whether the user explicitly provided a pod name.
            pod_name_match = re.search(
                r"\b(?:pod\s+)?([a-z0-9](?:[a-z0-9.-]*[a-z0-9])?)\s+"
                r"(?:pod\s+)?(?:crashing|crashed|failing|failed|logs?|events?)\b",
                question_lower,
            )

            if pod_name_match and not requested_pod:
                candidate_pod = pod_name_match.group(1)

                if candidate_pod not in {
                    "agent",
                    "mcp",
                    "frontend",
                    "pod",
                    "pods",
                }:
                    requested_pod = candidate_pod

            # Fallback for questions describing abnormal behavior.
            if not requested_pod and investigation_intent:
                abnormal_pod_match = re.search(
                    r"\b(?:is|are|check|investigate|troubleshoot)\s+"
                    r"([a-z0-9](?:[a-z0-9.-]*[a-z0-9])?)\s+"
                    r"(?=(?:showing|experiencing|having|in)\b)",
                    question_lower,
                )

                if abnormal_pod_match:
                    candidate_pod = abnormal_pod_match.group(1)

                    if candidate_pod not in {
                        "agent",
                        "mcp",
                        "frontend",
                        "pod",
                        "pods",
                    }:
                        requested_pod = candidate_pod

            # Prefer an exact match against actual pods returned by Kubernetes.
            available_pod_names = {
                pod.get("name")
                for pod in pod_context
                if isinstance(pod, dict) and pod.get("name")
            }

            explicit_pod_name = next(
                (
                    pod_name
                    for pod_name in sorted(
                        available_pod_names,
                        key=len,
                        reverse=True,
                    )
                    if re.search(
                        rf"(?<![a-z0-9.-]){re.escape(pod_name)}(?![a-z0-9.-])",
                        question_lower,
                    )
                ),
                None,
            )

            
            if explicit_pod_name:
                requested_pod = explicit_pod_name
            elif requested_pod not in available_pod_names:
                # Ignore regex guesses that are not real pods in this namespace.
                requested_pod = None

            logger.info(
                "Resolved explicit pod candidate: %s",
                requested_pod,
            )


            # If no explicit pod was supplied, resolve by logical component.
            if not requested_pod and not ownership_intent:

                if "frontend" in question_lower:
                    component = "frontend"

                elif "mcp" in question_lower:
                    component = "mcp"

                elif "agent" in question_lower:
                    component = "agent"

                else:
                    # Default to the agent when the user simply asks for logs.
                    component = "agent"

            logger.info(
                "Requested component: %s",
                component,
            )

            logger.info(
                "Explicit requested pod: %s",
                requested_pod,
            )

            # =========================================================
            # Dynamically resolve namespace for an explicit pod
            # =========================================================
            if requested_pod and not namespace_match:
                logger.info(
                    "No namespace supplied for explicit pod %s; "
                    "searching across all namespaces",
                    requested_pod,
                )

                all_pods_result = await call_mcp_tool(
                    KUBERNETES_MCP_URL,
                    "list_pods",
                    {},
                )

                if all_pods_result.is_error:
                    raise RuntimeError(
                        f"Unable to resolve namespace for pod '{requested_pod}': "
                        f"{all_pods_result}"
                    )

                all_pods = (
                    all_pods_result.structured_content.get("result", [])
                    if all_pods_result.structured_content
                    else []
                )

                matching_pod = next(
                    (
                        pod
                        for pod in all_pods
                        if pod.get("name") == requested_pod
                    ),
                    None,
                )

                if not matching_pod:
                    raise ValueError(
                        f"Pod '{requested_pod}' was not found "
                        "in any Kubernetes namespace."
                    )

                requested_namespace = matching_pod.get("namespace")

                logger.info(
                    "Dynamically resolved pod %s to namespace %s",
                    requested_pod,
                    requested_namespace,
                )

                # Refresh pod context using the dynamically discovered namespace.
                pod_result = await call_mcp_tool(
                    KUBERNETES_MCP_URL,
                    "list_pods",
                    {
                        "namespace": requested_namespace,
                    },
                )

                if pod_result.is_error:
                    raise RuntimeError(
                        f"Unable to retrieve pods from dynamically resolved "
                        f"namespace '{requested_namespace}': {pod_result}"
                    )

                pod_context = (
                    pod_result.structured_content.get("result", [])
                    if pod_result.structured_content
                    else []
                )

                logger.info(
                    "Refreshed pod context for dynamically resolved namespace %s",
                    requested_namespace,
                )

            if requested_pod:

                # -----------------------------------------------------
                # Explicit pod name supplied by the user.
                # Validate it against the current pod list.
                # -----------------------------------------------------
                current_pod_names = {
                    pod.get("name")
                    for pod in pod_context
                    if pod.get("name")
                }

                if requested_pod not in current_pod_names:
                    raise ValueError(
                        f"Pod '{requested_pod}' was not found in "
                        f"namespace '{requested_namespace}'."
                    )

                logger.info(
                    "Validated explicit pod: %s",
                    requested_pod,
                )

            
            else:
                # -----------------------------------------------------
                # No explicit pod name.
                # For an investigation, select the target from live pod
                # evidence instead of assuming it is the agent pod.
                # For other requests, retain component-based resolution.
                # -----------------------------------------------------
                if investigation_intent:
                    issue_keywords = {
                        "imagepullbackoff": ("imagepullbackoff", "image pull"),
                        "errimagepull": ("errimagepull",),
                        "crashloopbackoff": ("crashloopbackoff", "crash loop"),
                        "readiness": ("readiness", "not ready", "unready"),
                        "unschedulable": (
                            "unschedulable",
                            "failedscheduling",
                            "failed scheduling",
                            "podscheduled=false",
                            "insufficient cpu",
                            "insufficient memory",
                            "didn't match pod affinity",
                            "didn't match node selector",
                            "untolerated taint",
                        ),
                    }

                    matching_issue_keywords = next(
                        (
                            keywords
                            for issue, keywords in issue_keywords.items()
                            if issue in question_lower
                            or any(
                                keyword in question_lower
                                for keyword in keywords
                            )
                        ),
                        (),
                    )

                    def pod_matches_issue(pod, issue_keywords):
                        import json

                        # Inspect the complete pod record, including nested
                        # Kubernetes container status and waiting reasons.
                        pod_text = json.dumps(pod, default=str).lower()

                        status = pod.get("status", {})
                        if isinstance(status, dict):
                            container_statuses = status.get(
                                "containerStatuses", []
                            )
                        else:
                            container_statuses = []

                        for container in container_statuses:
                            state = container.get("state", {})
                            waiting = (
                                state.get("waiting", {})
                                if isinstance(state, dict)
                                else {}
                            )

                            pod_text += " " + str(
                                waiting.get("reason", "")
                            ).lower()
                            pod_text += " " + str(
                                waiting.get("message", "")
                            ).lower()

                        # Support flattened MCP response fields too.
                        pod_text += " " + " ".join(
                            str(pod.get(key, ""))
                            for key in (
                                "reason",
                                "message",
                                "container_statuses",
                                "containerStatuses",
                            )
                        ).lower()

                        return any(
                            keyword.lower() in pod_text
                            for keyword in issue_keywords
                        )

                    
                    health_check_intent = (
                        any(term in question_lower for term in (
                            "health of",
                            "health check",
                            "healthy pod",
                            "pod health",
                            "check pod health",
                            "check the pod",
                            "check pod status",
                            "are my pods healthy",
                            "are the pods healthy",
                            "is the pod healthy",
                            "is this pod healthy",
                            "pod health status",
                        ))
                        and not matching_issue_keywords
                    )

                    if health_check_intent:
                        total_pods = len(pod_context)
                        healthy_pods = []
                        unhealthy_pods = []

                        for pod in pod_context:
                            pod_name = pod.get("name", "unknown")
                            pod_status = str(pod.get("status", "Unknown"))
                            ready = pod.get("ready")
                            container_statuses = (
                                pod.get("container_statuses")
                                or pod.get("containerStatuses")
                                or []
                            )

                            issues = []

                            # Inspect pod-level status.
                            if pod_status != "Running":
                                issues.append(f"Pod status is {pod_status}")

                            # Inspect container readiness and waiting reasons.
                            for container in container_statuses:
                                if not isinstance(container, dict):
                                    continue

                                state = container.get("state") or {}
                                waiting = state.get("waiting") or {}
                                reason = waiting.get("reason")

                                if reason:
                                    issues.append(f"Container waiting reason: {reason}")

                                if container.get("ready") is False:
                                    issues.append("Container is not ready")

                                restart_count = container.get("restartCount", 0)
                                if restart_count:
                                    logger.info(
                                        "HEALTH CHECK: pod=%s container=%s restarts=%s",
                                        pod_name,
                                        container.get("name", "unknown"),
                                        restart_count,
                                    )

                            # Accept common flattened readiness representations.
                            if ready is False or (
                                isinstance(ready, str)
                                and ready.lower() in ("false", "0", "0/1")
                            ):
                                issues.append("Pod is not ready")

                            if issues:
                                unhealthy_pods.append({
                                    "name": pod_name,
                                    "status": pod_status,
                                    "issues": list(dict.fromkeys(issues)),
                                })
                            else:
                                healthy_pods.append({
                                    "name": pod_name,
                                    "status": pod_status,
                                })

                        logger.info(
                            "HEALTH CHECK SUMMARY: namespace=%s total=%s healthy=%s unhealthy=%s",
                            requested_namespace,
                            total_pods,
                            len(healthy_pods),
                            len(unhealthy_pods),
                        )

                        health_context = [
                            f"Namespace: {requested_namespace}",
                            f"Total pods: {total_pods}",
                            f"Healthy pods: {len(healthy_pods)}",
                            f"Unhealthy pods: {len(unhealthy_pods)}",
                        ]

                        for pod in healthy_pods:
                            health_context.append(
                                f"HEALTHY: {pod['name']} — {pod['status']}"
                            )

                        for pod in unhealthy_pods:
                            pod_name = pod["name"]
                            issue_text = ", ".join(pod["issues"])

                            health_context.append(
                                f"UNHEALTHY: {pod_name} — {pod['status']}; "
                                f"Issues: {issue_text}"
                            )

                            health_context.append(
                                f"Recommended actions for {pod_name}:"
                            )

                            if "ImagePullBackOff" in issue_text or "ErrImagePull" in issue_text:
                                health_context.extend([
                                    "- Verify the image name and tag in the pod specification.",
                                    "- Check registry access and image pull secrets if applicable.",
                                    f"- Verification: kubectl describe pod {pod_name} "
                                    f"-n {requested_namespace}",
                                    f"- Check events: kubectl get events -n {requested_namespace} "
                                    "--sort-by=.lastTimestamp",
                                ])

                            elif "CrashLoopBackOff" in issue_text:
                                health_context.extend([
                                    "- Inspect the container's current and previous logs.",
                                    "- Check the container command, arguments, configuration, "
                                    "and termination details.",
                                    f"- Current logs: kubectl logs {pod_name} "
                                    f"-n {requested_namespace}",
                                    f"- Previous logs: kubectl logs {pod_name} "
                                    f"-n {requested_namespace} --previous",
                                    f"- Verification: kubectl get pod {pod_name} "
                                    f"-n {requested_namespace}",
                                ])

                            elif "not ready" in issue_text.lower():
                                health_context.extend([
                                    "- Inspect readiness probe settings, application health, "
                                    "and container events.",
                                    f"- Verification: kubectl describe pod {pod_name} "
                                    f"-n {requested_namespace}",
                                    f"- Check readiness: kubectl get pod {pod_name} "
                                    f"-n {requested_namespace}",
                                ])

                            elif pod["status"] == "Pending":
                                health_context.extend([
                                    "- Inspect pod events to identify image, scheduling, "
                                    "resource, affinity, selector, or taint issues.",
                                    f"- Verification: kubectl describe pod {pod_name} "
                                    f"-n {requested_namespace}",
                                    f"- Check nodes: kubectl get nodes",
                                ])

                            else:
                                health_context.extend([
                                    "- Inspect the pod description, container states, and events "
                                    "to determine the underlying cause.",
                                    f"- Verification: kubectl describe pod {pod_name} "
                                    f"-n {requested_namespace}",
                                ])


                        health_context.append(
                            "For unhealthy pods, recommend evidence-based corrective actions "
                            "and namespace-specific kubectl verification commands. "
                            "Distinguish observed evidence from suspected causes."
                        )

                        mcp_context = "\n".join(health_context)


                    elif matching_issue_keywords:
                        candidates = [
                            pod for pod in pod_context
                            if pod.get("name")
                            and pod_matches_issue(pod, matching_issue_keywords)
                        ]

                        logger.info(
                            "ISSUE MATCH: keywords=%s candidates=%s",
                            matching_issue_keywords,
                            [pod.get("name") for pod in candidates],
                        )

                        if len(candidates) == 1:
                            requested_pod = candidates[0]["name"]
                        elif len(candidates) > 1:
                            raise ValueError(
                                f"Multiple pods match the requested issue: "
                                f"{[pod.get('name') for pod in candidates]}. "
                                "Please specify a pod name."
                            )
                        else:
                            raise ValueError(
                                f"No pod matching the requested issue was found "
                                f"in namespace {requested_namespace}."
                            )
                        logger.info(
                            "SELECTED INVESTIGATION POD: %s",
                            requested_pod,
                        )

                    else:
                        raise ValueError(
                            "Please specify the issue to investigate, "
                            "such as ImagePullBackOff, CrashLoopBackOff, "
                            "readiness failure, or an unschedulable pod."
                        )

                else:
                    # Preserve existing behavior for non-investigation
                    # component-specific requests.
                    pod_prefix = {
                        "agent": "kube-insightaiv2-agent-",
                        "mcp": "kube-insightaiv2-mcp-",
                        "frontend": "kube-insightaiv2-frontend-",
                    }[component]

                    for pod in pod_context:
                        pod_name = pod.get("name", "")

                        if pod_name.startswith(pod_prefix):
                            requested_pod = pod_name
                            break

                    if not requested_pod:
                        raise ValueError(
                            f"Could not find the current {component} pod "
                            f"in namespace '{requested_namespace}'."
                        )

                    logger.info(
                        "Resolved current %s pod: %s",
                        component,
                        requested_pod,
                    )

            logger.info(
                "Resolved pod for MCP request: %s",
                requested_pod,
            )

            investigation_owner = None

            logger.info(
                "BEFORE OWNER LOOKUP: requested_pod=%s ownership_intent=%s investigation_intent=%s",
                requested_pod,
                ownership_intent,
                investigation_intent,
            )

            if (investigation_intent or ownership_intent) and requested_pod:
                logger.info(
                    "Retrieving owner for pod %s in namespace %s",
                    requested_pod,
                    requested_namespace,
                )

                owner_result = await call_mcp_tool(
                    KUBERNETES_MCP_URL,
                    "get_pod_owner",
                    {
                        "pod_name": requested_pod,
                        "namespace": requested_namespace,
                    },
                )

                investigation_owner = parse_mcp_result(owner_result)

                logger.info(
                    "Owner result for %s: %s",
                    requested_pod,
                    investigation_owner,
                )
            # Keep ownership context and continue to final LLM response generation.
            if ownership_intent and not investigation_intent:
                mcp_context = {
                    "pod": pod_context,
                    "owner": investigation_owner,
                }

                logger.info(
                    "FINAL OWNERSHIP MCP CONTEXT BEFORE LLM: %s",
                    mcp_context,
                )

            # =========================================================
            # Investigation: retrieve events for the resolved pod
            # =========================================================
            if investigation_intent and requested_pod:
                logger.info(
                    "Investigation: retrieving events for pod %s in namespace %s",
                    requested_pod,
                    requested_namespace,
                )

                event_result = await call_mcp_tool(
                    KUBERNETES_MCP_URL,
                    "list_events",
                    {"namespace": requested_namespace},
                )

                if event_result.is_error:
                    logger.warning(...)
                    investigation_events = []
                else:
                    event_context = (
                        event_result.structured_content.get("result", [])
                        if event_result.structured_content
                        else []
                    )

                    investigation_events = []

                    for event in event_context:
                        event_object = event.get("object") or ""
                        event_message = event.get("message") or ""

                        if event_object == requested_pod:
                            investigation_events.append(event)
                        elif requested_pod in event_message:
                            investigation_events.append(event)

                    logger.info(
                        "Investigation events found for %s: %d",
                        requested_pod,
                        len(investigation_events),
                    )

                # Investigation: retrieve pod logs
                logger.info(
                    "Investigation: retrieving logs for pod %s in namespace %s",
                    requested_pod,
                    requested_namespace,
                )

                log_result = await call_mcp_tool(
                    KUBERNETES_MCP_URL,
                    "get_pod_logs",
                    {
                        "pod_name": requested_pod,
                        "namespace": requested_namespace,
                        "tail_lines": 100,
                    },
                )

                if log_result.is_error:
                    logger.warning(
                        "Investigation log retrieval failed for %s",
                        requested_pod,
                    )
                    investigation_logs = (
                        "Logs unavailable because the container "
                        "has not started successfully."
                    )
                else:
                    investigation_logs = ""

                    if log_result.content:
                        for item in log_result.content:
                            if hasattr(item, "text"):
                                investigation_logs += item.text

                    if investigation_logs.startswith("Kubernetes MCP error:"):
                        logger.warning(
                            "Pod logs unavailable for %s: %s",
                            requested_pod,
                            investigation_logs,
                        )

                        investigation_logs = (
                            "Logs unavailable because the container "
                            "has not started successfully."
                        )

                mcp_context = {
                    "pod": pod_context,
                    "owner": investigation_owner,
                    "events": investigation_events,
                    "logs": investigation_logs,
                }

            if not investigation_intent and not ownership_intent:
                start_time, end_time = extract_log_time_range(question)

                if start_time and end_time:
                    logger.info(
                        f"MCP time-range log request: {start_time} → {end_time}"
                    )

                    result = await call_mcp_tool(
                        KUBERNETES_MCP_URL,
                        "get_pod_logs_by_time",
                        {
                            "pod_name": requested_pod,
                            "namespace": requested_namespace,
                            "start_time": start_time,
                            "end_time": end_time,
                        },
                    )

                else:
                    logger.info("MCP standard log request")

                    result = await call_mcp_tool(
                        KUBERNETES_MCP_URL,
                        "get_pod_logs",
                        {
                            "pod_name": requested_pod,
                            "namespace": requested_namespace,
                            "tail_lines": 100,
                        },
                    )

            log_result = await call_mcp_tool(
                KUBERNETES_MCP_URL,
                "get_pod_logs",
                {
                    "pod_name": requested_pod,
                    "namespace": requested_namespace,
                    "tail_lines": 100,
                },
            )

            if log_result.is_error:
                logger.warning(
                    "Investigation log retrieval failed for %s: %s",
                    requested_pod,
                    log_result,
                )
                investigation_logs = "Unable to retrieve pod logs."
            else:
                investigation_logs = log_result.content

        # ---------------------------------------------------------
        # Deployments
        # ---------------------------------------------------------
        elif any(
            keyword in question_lower
            for keyword in (
                "deployment",
                "deployments",
            )
        ):
            logger.info("MCP tool selected: list_deployments")

            result = await call_mcp_tool(
                KUBERNETES_MCP_URL,
                "list_deployments",
                {
                    "namespace": requested_namespace,
                },
            )

        # ---------------------------------------------------------
        # Services
        # ---------------------------------------------------------
        elif any(
            keyword in question_lower
            for keyword in (
                "service",
                "services",
            )
        ):
            logger.info("MCP tool selected: list_services")

            result = await call_mcp_tool(
                KUBERNETES_MCP_URL,
                "list_services",
                {
                    "namespace": requested_namespace,
                },
            )

        # ---------------------------------------------------------
        # Events
        # ---------------------------------------------------------
        elif any(
            keyword in question_lower
            for keyword in (
                "event",
                "events",
            )
        ):
            logger.info("MCP event request detected")

            # Extract requested time range.
            start_time, end_time = extract_log_time_range(question)

            # =========================================================
            # Validate resolved pod against current pod list
            # =========================================================

            if requested_pod:
                current_pod_names = {
                    pod.get("name")
                    for pod in pod_context
                    if pod.get("name")
                }

                logger.info(
                    "CURRENT PODS FROM MCP: %s",
                    sorted(current_pod_names),
                )

                logger.info(
                    "RESOLVED REQUESTED POD: %s",
                    requested_pod,
                )

                if requested_pod not in current_pod_names:
                    logger.warning(
                        "Resolved pod %s is not present in current pod list. "
                        "Current pods: %s",
                        requested_pod,
                        sorted(current_pod_names),
                    )

                    requested_pod = None

            # =========================================================
            # Final pod validation
            # =========================================================

            if requested_pod:
                current_pod_names = {
                    pod.get("name")
                    for pod in pod_context
                    if pod.get("name")
                }

                if requested_pod not in current_pod_names:
                    logger.warning(
                        "Requested pod %s is not a current pod. Ignoring pod-specific filtering.",
                        requested_pod,
                    )
                    requested_pod = None
                else:
                    logger.info(
                        "Validated current pod: %s",
                        requested_pod,
                    )

            # =========================================================
            # Retrieve events
            # =========================================================
            if start_time and end_time:
                logger.info(
                    "MCP time-range event request: %s → %s",
                    start_time,
                    end_time,
                )

                result = await call_mcp_tool(
                    KUBERNETES_MCP_URL,
                    "list_events_by_time",
                    {
                        "namespace": requested_namespace,
                        "start_time": start_time,
                        "end_time": end_time,
                    },
                )

            else:
                logger.info("MCP standard event request")

                result = await call_mcp_tool(
                    KUBERNETES_MCP_URL,
                    "list_events",
                    {
                        "namespace": requested_namespace,
                    },
                )

            filtered_events = []

            event_context = (
                result.structured_content.get("result", [])
                if result.structured_content and not result.is_error
                else []
            )

            if requested_pod:
                filtered_events = []

                for event in event_context:

                    event_object = event.get("object") or ""
                    event_message = event.get("message") or ""

                    # Exact pod event
                    if event_object == requested_pod:
                        filtered_events.append(event)
                        continue

                    # Controller event explicitly referencing this pod
                    if requested_pod in event_message:
                        filtered_events.append(event)

                mcp_context = filtered_events

                logger.info(
                    "Passing %d filtered events to final LLM for pod %s",
                    len(mcp_context),
                    requested_pod,
                )

            else:
                # Normal namespace-wide event request
                mcp_context = event_context

                logger.info(
                    "Passing %d namespace-wide events to final LLM",
                    len(mcp_context),
                )

        # ---------------------------------------------------------
        # Pods
        # ---------------------------------------------------------
        elif any(
            keyword in question_lower
            for keyword in (
                "pod",
                "pods",
                "running",
                "status",
                "ready",
                "readiness",
                "health",
                "healthy",
            )
        ):
            logger.info("MCP tool selected: list_pods")

            result = await call_mcp_tool(
                KUBERNETES_MCP_URL,
                "list_pods",
                {
                    "namespace": requested_namespace,
                },
            )
        # ---------------------------------------------------------
        # Default
        # ---------------------------------------------------------
        else:
            logger.info("MCP default tool selected: list_pods")

            result = await call_mcp_tool(
                KUBERNETES_MCP_URL,
                "list_pods",
                {
                    "namespace": "kube-insightaiv2",
                },
            )

        # =========================================================
        # Validate MCP result
        # =========================================================

        if not investigation_intent and not ownership_intent:
            if result.is_error:
                raise RuntimeError(
                    f"MCP tool returned an error: {result}"
                )

        # mcp_context is already prepared by the specific MCP workflow.
        # Do not overwrite filtered event/log context with the raw MCP result.
        # Preserve context prepared by the specific MCP workflow.
        # Only use the generic result when it has been assigned.
        if "mcp_context" not in locals():
            if "result" not in locals() or result is None:
                raise RuntimeError(
                    "MCP workflow did not produce investigation context "
                    "or a valid tool result."
                )

            if result.is_error:
                raise RuntimeError(f"MCP tool returned an error: {result}")

            structured_content = result.structured_content or {}
            mcp_context = structured_content.get("result", [])

        # =========================================================
        # Generate final natural-language response
        # =========================================================

        prompt = f"""
        You are Kube-InsightAI, a Kubernetes and DevOps assistant.

        Answer the user's question using only the live Kubernetes
        information provided below.

        User question:
        {question}

        Live Kubernetes information:
        {mcp_context}

        Rules:

        1. Clearly distinguish live cluster information from general knowledge.
        2. Do not invent Kubernetes resources, logs, events, namespaces, or statuses.
        3. Use Markdown formatting.
        4. Use headings when useful.
        5. Keep the response practical and concise.
        6. If the live information does not contain enough information to answer,
        clearly say so.
        7. Do not claim to have inspected information that was not provided by MCP.
        8. Preserve Kubernetes resource names, URLs, IP addresses,
        timestamps, status values, and log lines exactly as provided.
        9. Never alter, correct, normalize, or paraphrase literal log content.
        10. When presenting events for a specific pod, include only events
            belonging to that exact pod.
        11. Never include events belonging to another pod, even if the pod
            belongs to the same application or workload.
        12. If the user asks for Kubernetes events and event data is available,
            present the events as a Markdown table.
        13. For Kubernetes events, use exactly these columns:
            | Timestamp | Type | Reason | Object | Message |
        14. Map the event fields as follows:
            - Timestamp → timestamp
            - Type → type
            - Reason → reason
            - Object → object
            - Message → message
        15. Preserve these field values exactly as provided.
        16. Do not expose raw Python dictionaries.
        17. Do not expose raw JSON.
        18. Do not include fields such as name, namespace, count,
            first_timestamp, last_timestamp, or object_kind
            unless explicitly requested.
        19. Do not output an "Event data:" section containing JSON.
        20. If the user asks for Kubernetes events and the MCP request
            succeeds but returns no matching events, clearly state that
            no Kubernetes events were found for the requested namespace,
            pod, or time range.
        21. Do not say that live Kubernetes information was unavailable
            when MCP successfully returned an empty event result.
        22. Only say that live Kubernetes information could not be
            retrieved when the MCP request actually failed or returned
            an error.
        23. Treat the "Live Kubernetes information" above as authoritative.
            Do not reconstruct or infer additional events from other data.
        24. When the user requests a pod health check, present the total pod count, healthy pod count, and unhealthy pod count.
        25. For every unhealthy pod, include its name, observed status, and the issues explicitly provided in the live Kubernetes information.
        26. Present the "Recommended actions" and verification commands provided for each unhealthy pod. Do not omit them merely to keep the response concise.
        27. Distinguish observed evidence from suspected causes. Do not claim a root cause unless the provided evidence supports it.
        28. Do not invent corrective actions, command output, or verification results.
        """

        try:

            llm = get_chat_model()

            logger.info(
                "FINAL MCP CONTEXT BEFORE LLM: %s",
                json.dumps(mcp_context, indent=2),
            )


            response = await llm.ainvoke(prompt)

            answer = str(response.content)

            return {
                "messages": [AIMessage(content=answer)],
                "answer": answer,
                "context": mcp_context,
                "sources": ["MCP: Kubernetes cluster"],
            }

        except Exception as exc:

            logger.exception("MCP response generation failed")

            return {
                "error": "Unable to retrieve live Kubernetes information.",
                "error_message": str(exc),
            }

    except Exception as exc:

        logger.exception("MCP response failed")

        return {
            "error": "Unable to process Kubernetes MCP request.",
            "error_message": str(exc),
        }

async def rca_response(state: AgentState) -> dict:
    """Analyze live Kubernetes investigation evidence and determine the most likely root cause."""

    question = extract_question(state)
    context = state.get("context", "")

    if not context:
        return {
            "answer": (
                "I could not perform the root cause analysis because "
                "no live Kubernetes investigation evidence was available."
            ),
        }

    prompt = f"""
You are Kube-InsightAI, a Kubernetes Root Cause Analysis and Recommendations assistant.

Analyze the user's Kubernetes investigation request using ONLY the live Kubernetes evidence provided below.

User question:
{question}

Live Kubernetes investigation evidence:
{json.dumps(context, indent=2, default=str)}

Your task is to explain what the evidence reveals and recommend appropriate next steps based on that evidence.

Rules:

1. Do not invent Kubernetes resources, events, logs, statuses, timestamps, configuration values, or other cluster information.

2. Treat the provided MCP evidence as authoritative for all claims about the current cluster.

3. Reason across all available evidence:
   - Pod state
   - Owner
   - Kubernetes events
   - Container logs

4. Identify the most likely root cause only when the evidence supports it.

5. Distinguish clearly between:
   - Confirmed evidence
   - Likely root cause
   - Possible contributing factors

6. If the evidence is insufficient to determine a root cause, explicitly say that the root cause cannot be determined from the available evidence.

7. Do not claim certainty when the evidence only supports a hypothesis.

8. Assign a confidence level:
   - High
   - Medium
   - Low
   Briefly explain the confidence level using the available evidence.

9. Provide practical, evidence-based recommendations that address the identified problem. Explain why each recommended action is appropriate.

10. Do not assume a specific failure mechanism without supporting evidence. For example, ImagePullBackOff alone does not establish whether the image name, tag, registry availability, or credentials are responsible.

11. When the evidence is insufficient to recommend a specific remediation, recommend a targeted diagnostic check instead of guessing.

12. Separate immediate diagnostic checks from corrective actions. Prioritize verification and low-risk investigation before potentially disruptive changes.

13. Do not execute commands or claim to have executed them. Commands may be provided for the user to run manually.

14. Flag potentially disruptive actions, such as deleting pods, restarting workloads, modifying production resources, or changing access controls. Explain the risk and recommend confirming the diagnosis first.

15. Include verification steps that explain how the user can determine whether the recommended action resolved the issue. Commands must be relevant to the investigated resource and namespace when those details are available.

16. Preserve Kubernetes resource names, timestamps, status values, and literal log messages exactly as provided.

17. Use clear Markdown formatting and practical Kubernetes terminology.

Use this response structure:

## Root Cause Analysis

### Resource
Identify the investigated Kubernetes resource using the available evidence. If it cannot be identified, say so.

### Root Cause
State the most likely root cause and distinguish confirmed facts from hypotheses. If the cause cannot be determined, explicitly say so.

### Evidence
List the specific live evidence supporting the conclusion. Do not invent or reconstruct missing evidence.

### Impact
Explain the observed impact based only on the available evidence. Clearly identify any impact that remains unknown.

### Confidence
State High, Medium, or Low and briefly explain why.

## Recommended Actions

List prioritized actions appropriate to the findings. For each action:
- Explain what to check or change.
- Explain why it is relevant to the evidence.
- Identify any required caution or risk.

If the evidence is insufficient for a corrective action, state which diagnostic check should come first.

## Verification

Provide practical commands or checks the user can run manually to verify the diagnosis or confirm recovery. Use the actual resource names and namespace from the evidence when available. Do not invent resource names or claim that a verification command has been run.

If the evidence does not support a root cause, say so explicitly rather than guessing, and focus recommendations on gathering the missing evidence.
"""

    try:
        llm = get_chat_model()

        logger.info(
            "Starting RCA reasoning for question: %s",
            question,
        )

        response = await llm.ainvoke(prompt)
        answer = str(response.content)

        logger.info("RCA reasoning completed")

        return {
            "messages": [AIMessage(content=answer)],
            "answer": answer,
        }

    except Exception as exc:
        logger.exception("RCA response generation failed")

        return {
            "error": "Unable to perform root cause analysis.",
            "error_message": str(exc),
        }

async def kubernetes_response(state: AgentState) -> dict:
    """Generate a Kubernetes response using retrieved RAG context."""

    question = extract_question(state)
    analysis = state.get("analysis", "")
    context = state.get("context", "")

    if context:
        knowledge_context = context
    else:
        knowledge_context = (
            "No relevant information was retrieved from the Kubernetes "
            "knowledge base."
        )

    prompt = f"""
    You are Kube-InsightAI, a Kubernetes and DevOps troubleshooting assistant.

    Answer the user's question using the provided Kubernetes knowledge-base context.

    User question:
    {question}

    Question analysis:
    {analysis}

    Knowledge-base context:
    {knowledge_context}

    Response formatting rules:
    1. Use clear Markdown formatting.
    2. Start with a concise and direct answer.
    3. Use the following sections when they are relevant:
    ## Diagnosis
    ## Possible Causes
    ## Troubleshooting Steps
    ## Recommended Action
    ## Next Step
    4. Use numbered lists for troubleshooting procedures.
    5. Put kubectl and other terminal commands inside fenced code blocks.
    6. Use backticks for Kubernetes resource names, commands, and configuration values.
    7. Keep the response practical and easy to follow.
    8. Avoid unnecessary repetition.
    9. Do not invent pod names, namespaces, logs, events, or cluster-specific facts.
    10. Do not claim that you inspected a live Kubernetes cluster.
    11. If the knowledge base does not contain enough information, clearly state:
        "I don't have enough information in the available Kubernetes knowledge base."
    12. Adapt the response structure to the question. Do not include irrelevant sections.

    The knowledge-base context is the primary source of information.
    """

    try:
        llm = get_chat_model()
        response = await llm.ainvoke(prompt)
        answer = str(response.content)

        return {
            "messages": [AIMessage(content=answer)],
            "answer": answer,
        }

    except Exception as exc:
        logger.exception("Kubernetes response generation failed")

        return {
            "error": "llm_provider_unavailable",
            "error_message": (
                "The AI provider is temporarily unavailable. "
                "Please try again later."
            ),
            "error_detail": str(exc),
        }

async def general_response(state: AgentState) -> dict:
    """Generate a general DevOps response."""

    question = extract_question(state)
    analysis = state.get("analysis", "")

    # =========================================================
    # Generate final natural-language response
    # =========================================================

    prompt = f"""
    You are Kube-InsightAI, a Kubernetes and DevOps assistant.

    Answer the user's question using the live Kubernetes information
    retrieved through MCP.

    User question:
    {question}

    Live Kubernetes information:
    {json.dumps(state.get("context", ""), indent=2)}

    Rules:

    1. Clearly distinguish live cluster information from general knowledge.

    2. Do not invent Kubernetes resources, logs, events, namespaces,
    statuses, timestamps, or messages.

    3. Use clear Markdown formatting.

    4. Keep the response practical and concise.

    5. If the live Kubernetes information does not contain enough information
    to answer the question, clearly say so.

    6. Do not claim to have inspected information that was not provided by MCP.

    7. Preserve Kubernetes resource names, timestamps, status values,
    and literal log/event messages exactly as provided.

    8. For Kubernetes EVENTS:
    - NEVER display the raw Python dictionary.
    - NEVER display JSON.
    - NEVER display the event list using `{ ... }`.
    - Convert every event into a Markdown table.
    - Use exactly these columns:

        | Timestamp | Type | Reason | Object | Message |

    - Put one Kubernetes event on each table row.
    - Preserve the event values exactly as provided.
    - Do not omit events.
    - Do not invent events.

    9. Example event response format:

    ### Kubernetes Events

    | Timestamp | Type | Reason | Object | Message |
    |---|---|---|---|---|
    | 2026-10-03T07:07:48+00:00 | Normal | Scheduled | kube-insightaiv2-agent-xxx | Successfully assigned ... |
    | 2026-10-03T07:07:49+00:00 | Normal | Pulling | kube-insightaiv2-agent-xxx | Pulling image ... |

    10. For Kubernetes LOGS:
        - Preserve the original log lines exactly.
        - Put log lines inside a fenced code block.

    11. For Kubernetes EVENTS, the Markdown table requirement takes priority
        over any request to display the underlying data structure.

    12. Do not expose internal MCP response structures, Python dictionaries,
        `structured_content`, or JSON unless the user explicitly asks for them.
    """

    try:
        llm = get_chat_model()
        response = await llm.ainvoke(prompt)
        answer = str(response.content)

        return {
            "messages": [AIMessage(content=answer)],
            "answer": answer,
        }

    except Exception:
        logger.exception("General response generation failed")

        return {
            "error": "Unable to generate a response.",
        }

def choose_route(state: AgentState) -> str:
    """Return the route selected by the routing node."""

    return state.get("route", "general")

def choose_mcp_next(state: AgentState) -> str:
    """Decide whether MCP output requires RCA reasoning."""

    if state.get("investigation_intent", False):
        return "rca"

    return "end"

def build_graph():
    """Build and compile the Kube-InsightAI LangGraph workflow."""

    builder = StateGraph(AgentState)

    builder.add_node("analyze", analyze_question)
    builder.add_node("router", route_question)

    builder.add_node("retrieve_context", retrieve_context)
    builder.add_node("kubernetes", kubernetes_response)

    builder.add_node("mcp", mcp_response)
    builder.add_node("rca", rca_response)

    builder.add_node("general", general_response)

    builder.add_edge(START, "analyze")
    builder.add_edge("analyze", "router")

    builder.add_conditional_edges(
        "router",
        choose_route,
        {
            "kubernetes": "retrieve_context",
            "mcp": "mcp",
            "general": "general",
        },
    )

    builder.add_edge("retrieve_context", "kubernetes")

    builder.add_edge("kubernetes", END)

    builder.add_conditional_edges(
        "mcp",
        choose_mcp_next,
        {
            "rca": "rca",
            "end": END,
        },
    )

    builder.add_edge("rca", END)

    builder.add_edge("general", END)

    return builder.compile()


graph = build_graph()