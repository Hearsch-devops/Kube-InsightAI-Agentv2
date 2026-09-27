import asyncio
import logging
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph

from app.langgraph.state import AgentState
from app.llm.llm import get_chat_model
from app.mcp.client import MCPClient
from lc_demos.langchain_retriever_demo import retriever
from lc_demos.langchain_rag_chain import format_documents


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

LIVE_CLUSTER_KEYWORDS = (
    "running pods",
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
    "services",
    "service status",
    "running services",
    "which services",
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

    live_cluster_intent = (
        any(keyword in question for keyword in LIVE_CLUSTER_KEYWORDS)
        or (
            "pod" in question
            and ("running" in question or "status" in question)
        )
        or (
            "deployment" in question
            and (
                "running" in question
                or "status" in question
                or "health" in question
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

    if live_cluster_intent:
        route: Literal["mcp", "kubernetes", "general"] = "mcp"

    elif any(keyword in question for keyword in KUBERNETES_KEYWORDS):
        route = "kubernetes"

    else:
        route = "general"

    logger.info("Question routed to: %s", route)

    return {"route": route}

async def mcp_response(state: AgentState) -> dict:
    """Retrieve live Kubernetes information using MCP."""

    question = extract_question(state)

    client = MCPClient()

    try:
        logger.info("Connecting to Kubernetes MCP server")

        await client.connect()

        question_lower = question.lower()

        # Select the MCP tool based on the user's Kubernetes intent.
        # More specific intents are checked before generic pod keywords.
        if any(
            keyword in question_lower
            for keyword in (
                "log",
                "logs",
                "logging",
            )
        ):
            logger.info("MCP log request detected")

            # First retrieve the current pod list so we do not
            # hardcode a pod name.
            pod_result = await client.call_tool(
                "list_pods",
                {
                    "namespace": "kube-insightaiv2",
                },
            )

            if pod_result.is_error:
                raise RuntimeError(
                    f"Unable to list pods before retrieving logs: {pod_result}"
                )

            pod_context = pod_result.structured_content.get(
                "result",
                "",
            )

            # Resolve the requested pod using a simple deterministic match.
            requested_pod = None

            if "agent" in question_lower:
                for line in pod_context.splitlines():
                    if line.startswith("Pod:") and "agent" in line.lower():
                        requested_pod = line.replace("Pod:", "").strip()
                        break

            elif "frontend" in question_lower:
                for line in pod_context.splitlines():
                    if line.startswith("Pod:") and "frontend" in line.lower():
                        requested_pod = line.replace("Pod:", "").strip()
                        break

            if not requested_pod:
                raise ValueError(
                    "I could not identify which pod you want logs from."
                )

            logger.info(
                "Resolved pod for log request: %s",
                requested_pod,
            )

            result = await client.call_tool(
                "get_pod_logs",
                {
                    "pod_name": requested_pod,
                    "namespace": "kube-insightaiv2",
                    "tail_lines": 100,
                },
            )

        elif any(
            keyword in question_lower
            for keyword in (
                "deployment",
                "deployments",
            )
        ):
            logger.info("MCP tool selected: list_deployments")

            result = await client.call_tool(
                "list_deployments",
                {
                    "namespace": "kube-insightaiv2",
                },
            )

        elif any(
            keyword in question_lower
            for keyword in (
                "service",
                "services",
            )
        ):
            logger.info("MCP tool selected: list_services")

            result = await client.call_tool(
                "list_services",
                {
                    "namespace": "kube-insightaiv2",
                },
            )

        elif any(
            keyword in question_lower
            for keyword in (
                "event",
                "events",
            )
        ):
            logger.info("MCP tool selected: list_events")

            result = await client.call_tool(
                "list_events",
                {
                    "namespace": "kube-insightaiv2",
                    "limit": 20,
                },
            )

        elif any(
            keyword in question_lower
            for keyword in (
                "pod",
                "pods",
                "running",
                "status",
            )
        ):
            logger.info("MCP tool selected: list_pods")

            result = await client.call_tool(
                "list_pods",
                {
                    "namespace": "kube-insightaiv2",
                },
            )

        else:
            logger.info("MCP tool selected: list_pods")

            result = await client.call_tool(
                "list_pods",
                {
                    "namespace": "kube-insightaiv2",
                },
            )

        if result.is_error:
            raise RuntimeError(
                f"MCP tool returned an error: {result}"
            )

        mcp_context = result.structured_content.get(
            "result",
            "",
        )

        prompt = f"""
You are Kube-InsightAI, a Kubernetes and DevOps assistant.

Answer the user's question using the live Kubernetes information
retrieved through MCP.

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
10. When presenting logs, place the original log lines inside a code block.
"""

        llm = get_chat_model()
        response = await llm.ainvoke(prompt)
        answer = str(response.content)

        return {
            "messages": [AIMessage(content=answer)],
            "answer": answer,
            "context": mcp_context,
            "sources": ["MCP: Kubernetes cluster"],
        }

    except Exception:
        logger.exception("MCP response generation failed")

        return {
            "error": "Unable to retrieve live Kubernetes information.",
        }

    finally:
        await client.close()

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

    prompt = f"""
You are Kube-InsightAI, a helpful DevOps and AI assistant.

User question:
{question}

Question analysis:
{analysis}

Provide a clear, accurate, and practical answer.

Response formatting rules:
1. Use clear Markdown formatting.
2. Start with a direct answer or brief explanation.
3. Use headings when they improve readability.
4. Use numbered lists for procedures.
5. Put terminal commands inside fenced code blocks.
6. Use backticks for commands, filenames, and configuration values.
7. Keep the response concise and easy to understand.
8. Do not invent facts, system information, or user-specific details.
9. If important information is missing, clearly explain what is needed.
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

    builder.add_node("mcp", mcp_response)

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
    builder.add_edge("mcp", END)
    builder.add_edge("general", END)

    return builder.compile()


graph = build_graph()
