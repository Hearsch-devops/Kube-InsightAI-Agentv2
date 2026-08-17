import os
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


CALCULATOR_MCP_URL = os.getenv(
    "CALCULATOR_MCP_URL",
    "http://192.168.48.169:8001/mcp",
)

WEATHER_MCP_URL = os.getenv(
    "WEATHER_MCP_URL",
    "http://192.168.48.169:8002/mcp",
)


@asynccontextmanager
async def get_mcp_session(server_url: str):
    """
    Create and initialize a connection to an MCP server.
    """

    async with streamable_http_client(server_url) as (
        read_stream,
        write_stream,
    ):
        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:

            await session.initialize()

            yield session


async def list_mcp_tools(server_url: str):
    """
    Return the tools exposed by an MCP server.
    """

    async with get_mcp_session(server_url) as session:

        result = await session.list_tools()

        return result.tools


async def call_mcp_tool(
    server_url: str,
    tool_name: str,
    arguments: dict,
):
    """
    Call a tool on an MCP server and return its result.
    """

    async with get_mcp_session(server_url) as session:

        result = await session.call_tool(
            tool_name,
            arguments=arguments,
        )

        return result