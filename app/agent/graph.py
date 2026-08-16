from langchain_core.tools import StructuredTool
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from app.agent.state import AgentState
from app.llm.llm import get_chat_model
from app.mcp_client import call_mcp_tool


# =========================================================
# MCP Calculator Tool Wrappers
# =========================================================

async def calculator_add(a: float, b: float):
    result = await call_mcp_tool(
        "add",
        {
            "a": a,
            "b": b,
        },
    )

    return result.structured_content["result"]


async def calculator_subtract(a: float, b: float):
    result = await call_mcp_tool(
        "subtract",
        {
            "a": a,
            "b": b,
        },
    )

    return result.structured_content["result"]


async def calculator_multiply(a: float, b: float):
    result = await call_mcp_tool(
        "multiply",
        {
            "a": a,
            "b": b,
        },
    )

    return result.structured_content["result"]


async def calculator_divide(a: float, b: float):
    result = await call_mcp_tool(
        "divide",
        {
            "a": a,
            "b": b,
        },
    )

    return result.structured_content["result"]


# =========================================================
# Convert MCP functions into LangChain Tools
# =========================================================

calculator_tools = [
    StructuredTool.from_function(
        coroutine=calculator_add,
        name="add",
        description="Add two numbers together.",
    ),
    StructuredTool.from_function(
        coroutine=calculator_subtract,
        name="subtract",
        description="Subtract the second number from the first.",
    ),
    StructuredTool.from_function(
        coroutine=calculator_multiply,
        name="multiply",
        description="Multiply two numbers together.",
    ),
    StructuredTool.from_function(
        coroutine=calculator_divide,
        name="divide",
        description="Divide the first number by the second.",
    ),
]


# =========================================================
# LangGraph ToolNode
# =========================================================

tool_node = ToolNode(calculator_tools)


# =========================================================
# LLM
# =========================================================

llm = get_chat_model()

llm_with_tools = llm.bind_tools(calculator_tools)


# =========================================================
# LLM Node
# =========================================================

async def call_llm(state: AgentState):

    response = await llm_with_tools.ainvoke(
        state["messages"]
    )

    return {
        "messages": [response]
    }


# =========================================================
# Routing
# =========================================================

def route_after_llm(state: AgentState):

    last_message = state["messages"][-1]

    if last_message.tool_calls:
        return "tools"

    return END


# =========================================================
# Build LangGraph
# =========================================================

builder = StateGraph(AgentState)

builder.add_node("llm", call_llm)
builder.add_node("tools", tool_node)

builder.add_edge(START, "llm")

builder.add_conditional_edges(
    "llm",
    route_after_llm,
    {
        "tools": "tools",
        END: END,
    },
)

builder.add_edge("tools", "llm")

graph = builder.compile()