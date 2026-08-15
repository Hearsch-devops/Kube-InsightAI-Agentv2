import os
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


MCP_SERVER_URL = os.getenv(
    "MCP_SERVER_URL",
    "http://192.168.48.169:8001/mcp",
)


@asynccontextmanager
async def get_mcp_session():
    async with streamable_http_client(MCP_SERVER_URL) as (
        read_stream,
        write_stream,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session


async def list_mcp_tools():
    async with get_mcp_session() as session:
        result = await session.list_tools()
        return result.tools


async def call_mcp_tool(tool_name: str, arguments: dict):
    async with get_mcp_session() as session:
        result = await session.call_tool(
            tool_name,
            arguments=arguments,
        )

        return result