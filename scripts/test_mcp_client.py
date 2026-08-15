import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


MCP_SERVER_URL = "http://192.168.48.169:8001/mcp"


async def main():
    print("=" * 60)
    print("Connecting to Calculator MCP Server")
    print("=" * 60)

    async with streamable_http_client(MCP_SERVER_URL) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:

            # Initialize MCP session
            await session.initialize()

            print("\nMCP connection initialized successfully.")

            # Discover tools
            tools = await session.list_tools()

            print("\nAvailable MCP tools:")
            for tool in tools.tools:
                print(f" - {tool.name}: {tool.description}")

            # Call calculator tool
            result = await session.call_tool(
                "add",
                arguments={
                    "a": 25,
                    "b": 75,
                },
            )

            print("\nCalculator result:")
            print(result)


if __name__ == "__main__":
    asyncio.run(main())