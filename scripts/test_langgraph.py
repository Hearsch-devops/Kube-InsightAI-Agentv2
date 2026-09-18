import asyncio

from langchain_core.messages import HumanMessage

from app.langgraph.graph import graph


async def run_test(question: str):
    """Run a question through the asynchronous LangGraph workflow."""

    result = await graph.ainvoke(
        {
            "messages": [
                HumanMessage(content=question)
            ]
        }
    )

    print("\n===== LANGGRAPH RESPONSE =====")
    print(f"Question: {question}")
    print(f"Route: {result.get('route')}")
    print(f"Analysis: {result.get('analysis')}")
    print(f"Answer: {result.get('answer')}")
    print("==============================\n")


async def main():
    await run_test("Why do we use Kubernetes?")


if __name__ == "__main__":
    asyncio.run(main())
