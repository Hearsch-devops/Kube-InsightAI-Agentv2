from langgraph.graph import StateGraph, START, END

from app.agent.state import AgentState
from app.llm.llm import get_llm_response


def call_llm(state: AgentState):
    response = get_llm_response(state["message"])

    return {
        "response": response
    }


# Create the graph
builder = StateGraph(AgentState)

# Add our LLM node
builder.add_node("llm", call_llm)

# Define workflow
builder.add_edge(START, "llm")
builder.add_edge("llm", END)

# Compile graph
graph = builder.compile()