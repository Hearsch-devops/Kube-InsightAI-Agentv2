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

# ============================================================
# RAG Metrics
# ============================================================

RAG_RETRIEVALS = Counter(
    "kube_insightai_rag_retrievals_total",
    "Total number of RAG retrieval operations",
    ["status"],
)

RAG_RETRIEVAL_DURATION = Histogram(
    "kube_insightai_rag_retrieval_duration_seconds",
    "RAG vector retrieval duration in seconds",
)

RAG_DOCUMENTS_RETRIEVED = Histogram(
    "kube_insightai_rag_documents_retrieved",
    "Number of documents returned by RAG retrieval",
)

RAG_ERRORS = Counter(
    "kube_insightai_rag_errors_total",
    "Total number of RAG retrieval errors",
)


# Initialize metric series.
RAG_RETRIEVALS.labels(status="success")
RAG_RETRIEVALS.labels(status="error")

# ============================================================
# MCP Tool Metrics
# ============================================================

MCP_TOOL_CALLS = Counter(
    "kube_insightai_mcp_tool_calls_total",
    "Total number of MCP tool invocations",
    ["server", "tool", "status"],
)

MCP_TOOL_DURATION = Histogram(
    "kube_insightai_mcp_tool_duration_seconds",
    "MCP tool execution duration in seconds",
    ["server", "tool"],
)

MCP_TOOL_ERRORS = Counter(
    "kube_insightai_mcp_tool_errors_total",
    "Total number of MCP tool execution errors",
    ["server", "tool", "error_type"],
)


# Initialize known MCP server metric series.
MCP_SERVERS = (
    "kubernetes",
    "calculator",
    "weather",
    "unknown",
)

for server in MCP_SERVERS:
    MCP_TOOL_ERRORS.labels(
        server=server,
        tool="unknown",
        error_type="exception",
    )