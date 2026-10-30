from prometheus_client import Counter, Histogram


# ============================================================
# Agent Execution Metrics
# ============================================================

AGENT_RUNS = Counter(
    "kube_insightai_agent_runs_total",
    "Total number of agent executions",
    ["status"],
)

AGENT_RUN_DURATION = Histogram(
    "kube_insightai_agent_run_duration_seconds",
    "Complete agent execution duration in seconds",
)

AGENT_ERRORS = Counter(
    "kube_insightai_agent_errors_total",
    "Total number of agent execution errors",
    ["error_type"],
)


# Initialize metric series.
AGENT_RUNS.labels(status="success")
AGENT_RUNS.labels(status="error")

AGENT_ERRORS.labels(error_type="application")
AGENT_ERRORS.labels(error_type="exception")

# ============================================================
# LangGraph Node Metrics
# ============================================================

AGENT_NODE_EXECUTIONS = Counter(
    "kube_insightai_agent_node_executions_total",
    "Total number of LangGraph node executions",
    ["node"],
)

AGENT_NODE_DURATION = Histogram(
    "kube_insightai_agent_node_duration_seconds",
    "LangGraph node execution duration in seconds",
    ["node"],
)

AGENT_NODE_ERRORS = Counter(
    "kube_insightai_agent_node_errors_total",
    "Total number of LangGraph node execution errors",
    ["node"],
)


# Initialize metric series for all graph nodes.
GRAPH_NODES = (
    "analyze",
    "router",
    "retrieve_context",
    "kubernetes",
    "mcp",
    "rca",
    "general",
    "remediation",
)

for node in GRAPH_NODES:
    AGENT_NODE_EXECUTIONS.labels(node=node)
    AGENT_NODE_DURATION.labels(node=node)
    AGENT_NODE_ERRORS.labels(node=node)