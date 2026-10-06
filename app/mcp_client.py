from app.mcp_client import (
    call_mcp_tool,
    parse_mcp_result,
    KUBERNETES_MCP_URL,
)
import os
import json
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

KUBERNETES_MCP_URL = os.getenv(
    "KUBERNETES_MCP_URL",
    "http://kube-insightaiv2-mcp:8001/mcp",
)

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

def parse_mcp_result(result):
    """
    Convert MCP CallToolResult into a JSON-compatible
    Python object.
    """

    if result is None:
        return None

    # Prefer MCP structured content when available.
    if hasattr(result, "structured_content"):
        structured = result.structured_content

        if isinstance(structured, dict) and "result" in structured:
            return structured["result"]

        if structured is not None:
            return structured

    # Fallback to text content for compatibility.
    if hasattr(result, "content"):

        for item in result.content:

            if hasattr(item, "text"):

                text = item.text

                try:
                    return json.loads(text)

                except (json.JSONDecodeError, TypeError):
                    return text

    return result