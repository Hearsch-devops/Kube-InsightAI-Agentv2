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