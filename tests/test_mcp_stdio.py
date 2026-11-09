"""Exercise the actual MCP stdio handshake without a live API connection."""

import asyncio
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_stdio_discovers_journal_tools_and_rejects_bad_input_without_api():
    async def check():
        parameters = StdioServerParameters(
            command=sys.executable,
            args=[str(Path(__file__).resolve().parents[1] / "server.py")],
            env={"AJERA_API_URL": "https://example.invalid/api"},
        )
        async with stdio_client(parameters) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                response = await session.list_tools()
                names = {tool.name for tool in response.tools}
                assert {"list_journal_entries", "get_journal_entry"} <= names
                assert not any(name.startswith(("create_", "update_", "delete_", "void_"))
                               for name in names)
                result = await session.call_tool("get_journal_entry", {"journal_entry_keys": []})
                text = " ".join(item.text for item in result.content if item.type == "text")
                assert "Invalid request:" in text
                result = await session.call_tool(
                    "list_journal_entries", {"earliest_date": "2026-02-30"},
                )
                text = " ".join(item.text for item in result.content if item.type == "text")
                assert "Invalid request:" in text

    asyncio.run(check())
