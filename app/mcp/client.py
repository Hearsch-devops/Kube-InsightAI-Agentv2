import asyncio
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPClient:
    """Reusable MCP client for Kube-InsightAI."""

    def __init__(self):
        self.server_params = StdioServerParameters(
            command="python",
            args=[
                os.path.join(
                    os.path.dirname(__file__),
                    "server.py",
                )
            ],
        )

        self._stdio_context = None
        self._session_context = None
        self.session = None

    async def connect(self):
        """Start the MCP server and initialize the client session."""

        self._stdio_context = stdio_client(self.server_params)

        read_stream, write_stream = await self._stdio_context.__aenter__()

        self._session_context = ClientSession(
            read_stream,
            write_stream,
        )

        self.session = await self._session_context.__aenter__()

        await self.session.initialize()

    async def list_tools(self):
        """Return tools exposed by the MCP server."""

        if self.session is None:
            raise RuntimeError("MCP client is not connected.")

        result = await self.session.list_tools()
        return result.tools

    async def call_tool(self, tool_name, arguments=None):
        """Execute an MCP tool."""

        if self.session is None:
            raise RuntimeError("MCP client is not connected.")

        return await self.session.call_tool(
            tool_name,
            arguments or {},
        )

    async def close(self):
        """Close the MCP session and server process."""

        if self._session_context is not None:
            await self._session_context.__aexit__(None, None, None)
            self._session_context = None

        if self._stdio_context is not None:
            await self._stdio_context.__aexit__(None, None, None)
            self._stdio_context = None

        self.session = None


async def main():
    client = MCPClient()

    try:
        await client.connect()

        print("Connected to MCP server!")

        tools = await client.list_tools()

        print("\nAvailable tools:")
        for tool in tools:
            print(f"- {tool.name}")
#list_pods
        result = await client.call_tool(
            "list_pods",
            {"namespace": "kube-insightaiv2"},
        )

        print("\nlist_pods result:")
        print(result)
#get_pods_logs
        logs = await client.call_tool(
            "get_pod_logs",
            {
                "pod_name": "kube-insightaiv2-agent-7b47c6d66d-92tll",
                "namespace": "kube-insightaiv2",
                "tail_lines": 50,
            },
        )

        print("\nget_pod_logs result:")
        print(logs)
#list_deployments
        deployments = await client.call_tool(
        "list_deployments",
            {
                "namespace": "kube-insightaiv2",
            },
        )
        print("\nlist_deployments result:")
        print(deployments)

#list_events
        events = await client.call_tool(
        "list_events",
            {
                "namespace": "kube-insightaiv2",
                "limit": 20,
            },
        )

        print("\nlist_events result:")
        print(events)

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
