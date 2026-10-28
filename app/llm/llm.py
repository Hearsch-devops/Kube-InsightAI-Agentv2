
import os
import time
from typing import Any
from uuid import UUID

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from app.monitoring.llm_metrics import (
    LLM_REQUESTS,
    LLM_INPUT_TOKENS,
    LLM_OUTPUT_TOKENS,
    LLM_TOKEN_USAGE_UNAVAILABLE,
    LLM_REQUEST_DURATION,
)

load_dotenv()

TOKEN = os.getenv("LLMFOUNDRY_TOKEN")
PROJECT = os.getenv("PROJECT_NAME")

BASE_URL = "https://llmfoundry.straive.com/gemini/v1beta/openai"
MODEL = "models/gemini-2.5-flash"


class LLMMetricsCallback(BaseCallbackHandler):
    """Record LLM request metrics from LangChain callbacks."""

    def __init__(self) -> None:
        self._start_times: dict[str, float] = {}

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[Any]],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        self._start_times[str(run_id)] = time.perf_counter()

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        model = MODEL
        run_key = str(run_id)

        start = self._start_times.pop(run_key, None)
        if start is not None:
            LLM_REQUEST_DURATION.labels(model=model).observe(
                time.perf_counter() - start
            )

        LLM_REQUESTS.labels(model=model, status="success").inc()

        usage = None

        # OpenAI-compatible token usage, when returned by the provider.
        if response.llm_output:
            usage = response.llm_output.get("token_usage")

        input_tokens = None
        output_tokens = None

        if isinstance(usage, dict):
            input_tokens = usage.get("prompt_tokens")
            output_tokens = usage.get("completion_tokens")

        # Some LangChain messages expose normalized usage metadata instead.
        if input_tokens is None or output_tokens is None:
            for generation_list in response.generations:
                for generation in generation_list:
                    message = getattr(generation, "message", None)
                    metadata = getattr(message, "usage_metadata", None)
                    if metadata:
                        input_tokens = metadata.get("input_tokens", input_tokens)
                        output_tokens = metadata.get("output_tokens", output_tokens)
                        break
                if input_tokens is not None and output_tokens is not None:
                    break

        if input_tokens is not None and output_tokens is not None:
            LLM_INPUT_TOKENS.labels(model=model).inc(int(input_tokens))
            LLM_OUTPUT_TOKENS.labels(model=model).inc(int(output_tokens))
        else:
            LLM_TOKEN_USAGE_UNAVAILABLE.labels(model=model).inc()

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        model = MODEL
        start = self._start_times.pop(str(run_id), None)

        if start is not None:
            LLM_REQUEST_DURATION.labels(model=model).observe(
                time.perf_counter() - start
            )

        LLM_REQUESTS.labels(model=model, status="error").inc()


llm_metrics_callback = LLMMetricsCallback()


def get_chat_model() -> ChatOpenAI:
    """Create the LangChain chat model connected to LLMFoundry."""
    if not TOKEN:
        raise ValueError("LLMFOUNDRY_TOKEN is not configured")
    if not PROJECT:
        raise ValueError("PROJECT_NAME is not configured")

    return ChatOpenAI(
        model=MODEL,
        base_url=BASE_URL,
        api_key=f"{TOKEN}:{PROJECT}",
        temperature=0,
        callbacks=[llm_metrics_callback],
    )


def get_llm_response(message: str) -> str:
    """Call the configured LLM and return its response content."""
    llm = get_chat_model()
    response = llm.invoke(message)
    return response.content

