from prometheus_client import Counter, Histogram

LLM_REQUESTS = Counter(
    "kube_insightai_llm_requests_total",
    "Total LLM requests",
    ["model", "status"],
)

LLM_INPUT_TOKENS = Counter(
    "kube_insightai_llm_input_tokens_total",
    "Total input tokens reported by LLM responses",
    ["model"],
)

LLM_OUTPUT_TOKENS = Counter(
    "kube_insightai_llm_output_tokens_total",
    "Total output tokens reported by LLM responses",
    ["model"],
)

LLM_TOKEN_USAGE_UNAVAILABLE = Counter(
    "kube_insightai_llm_token_usage_unavailable_total",
    "LLM responses without token usage metadata",
    ["model"],
)

LLM_REQUEST_DURATION = Histogram(
    "kube_insightai_llm_request_duration_seconds",
    "LLM request duration in seconds",
    ["model"],
)


# Initialize metric series so they appear on /metrics before the first request.
MODEL = "models/gemini-2.5-flash"

LLM_REQUESTS.labels(model=MODEL, status="success")
LLM_REQUESTS.labels(model=MODEL, status="error")

LLM_INPUT_TOKENS.labels(model=MODEL)
LLM_OUTPUT_TOKENS.labels(model=MODEL)
LLM_TOKEN_USAGE_UNAVAILABLE.labels(model=MODEL)
LLM_REQUEST_DURATION.labels(model=MODEL)
