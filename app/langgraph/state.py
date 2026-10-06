from typing import Annotated, Literal

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    """Shared state passed between LangGraph nodes."""

    messages: Annotated[list[BaseMessage], add_messages]

    question: str
    analysis: str
    route: Literal["kubernetes", "mcp", "general"]

    requested_pod: str
    requested_namespace: str

    investigation_intent: bool
    ownership_intent: bool
    
    context: str
    sources: list[str]

    answer: str
    error: str
    error_message: str