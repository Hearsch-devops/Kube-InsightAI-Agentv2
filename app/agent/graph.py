from langchain_core.messages import ToolMessage
from langchain_core.tools import StructuredTool
from langgraph.graph import StateGraph, START, END

from app.agent.state import AgentState
from app.llm.llm import get_chat_model
from app.mcp_client import (
    call_mcp_tool,
    CALCULATOR_MCP_URL,
    WEATHER_MCP_URL,
)


# =========================================================
# MCP Calculator Tool Wrappers
# =========================================================

async def calculator_add(a: float, b: float):
    result = await call_mcp_tool(
        CALCULATOR_MCP_URL,
        "add",
        {
            "a": a,
            "b": b,
        },
    )

    return result.structured_content["result"]


async def calculator_subtract(a: float, b: float):
    result = await call_mcp_tool(
        CALCULATOR_MCP_URL,
        "subtract",
        {
            "a": a,
            "b": b,
        },
    )

    return result.structured_content["result"]


async def calculator_multiply(a: float, b: float):
    result = await call_mcp_tool(
        CALCULATOR_MCP_URL,
        "multiply",
        {
            "a": a,
            "b": b,
        },
    )

    return result.structured_content["result"]


async def calculator_divide(a: float, b: float):
    result = await call_mcp_tool(
        CALCULATOR_MCP_URL,
        "divide",
        {
            "a": a,
            "b": b,
        },
    )

    return result.structured_content["result"]


# =========================================================
# MCP Weather Tool Wrapper
# =========================================================

async def weather_get_weather(city: str):
    result = await call_mcp_tool(
        WEATHER_MCP_URL,
        "get_weather",
        {
            "city": city,
        },
    )

    if result.is_error:
        return result.content[0].text

    return result.content[0].text


# =========================================================
# Convert MCP functions into LangChain Tools
# =========================================================

agent_tools = [
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

    StructuredTool.from_function(
        coroutine=weather_get_weather,
        name="get_weather",
        description="Get the current weather for a city.",
    ),
]


# =========================================================
# LLM
# =========================================================

llm = get_chat_model()

llm_with_tools = llm.bind_tools(agent_tools)


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
# MCP Tool Node
# =========================================================

async def call_tools(state: AgentState):

    last_message = state["messages"][-1]

    print("\n========== MCP TOOL CALL ==========")

    tool_messages = []

    for tool_call in last_message.tool_calls:

        tool_name = tool_call["name"]
        arguments = tool_call["args"]
        tool_call_id = tool_call["id"]

        print(f"Tool   : {tool_name}")
        print(f"Args   : {arguments}")

        if tool_name == "add":
            result = await calculator_add(**arguments)

        elif tool_name == "subtract":
            result = await calculator_subtract(**arguments)

        elif tool_name == "multiply":
            result = await calculator_multiply(**arguments)

        elif tool_name == "divide":
            result = await calculator_divide(**arguments)

        elif tool_name == "get_weather":
            result = await weather_get_weather(**arguments)

        else:
            result = f"Unknown tool: {tool_name}"

        print(f"Result : {result}")
        print("===================================\n")

        tool_messages.append(
            ToolMessage(
                content=str(result),
                tool_call_id=tool_call_id,
            )
        )

    return {
        "messages": tool_messages
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
builder.add_node("tools", call_tools)

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