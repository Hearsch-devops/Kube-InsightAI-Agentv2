import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async def main():
    async with streamable_http_client(
        "http://127.0.0.1:8002/mcp"
    ) as (read_stream, write_stream):

        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tools = await session.list_tools()

            print("Available Weather tools:")
            for tool in tools.tools:
                print(f" - {tool.name}: {tool.description}")

            result = await session.call_tool(
                "get_weather",
                arguments={"city": "Mumbai"},
            )

            print("\nWeather result:")
            print(result)

asyncio.run(main())