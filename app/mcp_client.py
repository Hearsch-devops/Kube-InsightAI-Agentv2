
import os
import json
from contextlib import asynccontextmanager

import logging
logger = logging.getLogger(__name__)

from app.monitoring.agent_metrics import (
    MCP_TOOL_CALLS,
    MCP_TOOL_DURATION,
    MCP_TOOL_ERRORS,
)

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

def get_mcp_server_name(server_url: str) -> str:
    """Return a bounded MCP server label."""

    if server_url == KUBERNETES_MCP_URL:
        return "kubernetes"

    if server_url == CALCULATOR_MCP_URL:
        return "calculator"

    if server_url == WEATHER_MCP_URL:
        return "weather"

    return "unknown"

async def call_mcp_tool(
    server_url: str,
    tool_name: str,
    arguments: dict,
):
    """
    Call an MCP tool with Prometheus observability.
    """

    server = get_mcp_server_name(server_url)

    try:
        # Measure complete MCP invocation duration.
        with MCP_TOOL_DURATION.labels(
            server=server,
            tool=tool_name,
        ).time():

            async with get_mcp_session(server_url) as session:

                result = await session.call_tool(
                    tool_name,
                    arguments=arguments,
                )

        # Detect application-level MCP errors.
        if getattr(result, "is_error", getattr(result, "isError", False)):

            MCP_TOOL_CALLS.labels(
                server=server,
                tool=tool_name,
                status="error",
            ).inc()

            MCP_TOOL_ERRORS.labels(
                server=server,
                tool=tool_name,
                error_type="application",
            ).inc()

        else:

            MCP_TOOL_CALLS.labels(
                server=server,
                tool=tool_name,
                status="success",
            ).inc()

        return result

    except Exception:

        MCP_TOOL_CALLS.labels(
            server=server,
            tool=tool_name,
            status="error",
        ).inc()

        MCP_TOOL_ERRORS.labels(
            server=server,
            tool=tool_name,
            error_type="exception",
        ).inc()

        logger.exception(
            "MCP tool execution failed: server=%s, tool=%s",
            server,
            tool_name,
        )

        raise

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