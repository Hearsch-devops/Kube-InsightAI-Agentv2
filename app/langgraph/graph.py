import asyncio
import logging
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph

from app.langgraph.state import AgentState
from app.llm.llm import get_chat_model
from lc_demos.langchain_retriever_demo import retriever


logger = logging.getLogger(__name__)


KUBERNETES_KEYWORDS = (
    "kubernetes",
    "k8s",
    "pod",
    "deployment",
    "service",
    "kubectl",
    "namespace",
    "configmap",
    "secret",
    "ingress",
    "helm",
    "container",
    "node",
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


def route_question(state: AgentState) -> dict:
    """Route the question to the appropriate response workflow."""

    question = extract_question(state).lower()

    if any(keyword in question for keyword in KUBERNETES_KEYWORDS):
        route: Literal["kubernetes", "general"] = "kubernetes"
    else:
        route = "general"

    logger.info("Question routed to: %s", route)

    return {"route": route}


def format_documents(documents: list) -> tuple[str, list[str]]:
    """Convert retrieved documents into LLM context and source information."""

    context_parts = []
    sources = []

    for index, document in enumerate(documents, start=1):
        metadata = getattr(document, "metadata", {}) or {}
        content = str(getattr(document, "page_content", ""))

        source = str(metadata.get("source", "unknown"))
        chunk = str(metadata.get("chunk_index", "unknown"))

        context_parts.append(
            f"""
--- Document {index} ---
Source: {source}
Chunk: {chunk}

{content}
""".strip()
        )

        if source not in sources:
            sources.append(source)

    return "\n\n".join(context_parts), sources


async def retrieve_context(state: AgentState) -> dict:
    """Retrieve relevant Kubernetes SOP content from the vector database."""

    question = extract_question(state)

    try:
        logger.info("Retrieving RAG context for question")

        # Run the synchronous retriever in a worker thread.
        documents = await asyncio.to_thread(
            retriever.invoke,
            question,
        )

        context, sources = format_documents(documents)

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
You are Kube-InsightAI, a Kubernetes and DevOps assistant.

Answer the user's question using the provided knowledge-base context.

User question:
{question}

Question analysis:
{analysis}

Knowledge-base context:
{knowledge_context}

Rules:
- Use the knowledge-base context as the primary source of information.
- Do not invent facts or cluster-specific information.
- If the context does not contain the answer, clearly say:
  "I don't have enough information in the available Kubernetes knowledge base."
- Explain the answer clearly.
- Include kubectl commands only when useful.
- Do not claim that you inspected a live Kubernetes cluster.
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
        logger.exception("Kubernetes response generation failed")

        return {
            "error": "Unable to generate a Kubernetes response.",
        }


async def general_response(state: AgentState) -> dict:
    """Generate a general DevOps response."""

    question = extract_question(state)
    analysis = state.get("analysis", "")

    prompt = f"""
You are Kube-InsightAI, a helpful DevOps and AI assistant.

User question:
{question}

Question analysis:
{analysis}

Provide a clear and helpful answer.

Rules:
- Avoid inventing facts or system information.
- Explain concepts clearly.
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


def build_graph():
    """Build and compile the Kube-InsightAI LangGraph workflow."""

    builder = StateGraph(AgentState)

    builder.add_node("analyze", analyze_question)
    builder.add_node("router", route_question)
    builder.add_node("retrieve_context", retrieve_context)
    builder.add_node("kubernetes", kubernetes_response)
    builder.add_node("general", general_response)

    builder.add_edge(START, "analyze")
    builder.add_edge("analyze", "router")

    builder.add_conditional_edges(
        "router",
        choose_route,
        {
            "kubernetes": "retrieve_context",
            "general": "general",
        },
    )

    builder.add_edge("retrieve_context", "kubernetes")
    builder.add_edge("kubernetes", END)
    builder.add_edge("general", END)

    return builder.compile()


graph = build_graph()
