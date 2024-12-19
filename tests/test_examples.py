"""Tests for example servers"""

import pytest

from mcp.shared.memory import (
    create_connected_server_and_client_session as client_session,
)
from mcp.types import TextContent


@pytest.mark.anyio
async def test_simple_echo():
    """Test the simple echo server"""
    from examples.fastmcp.simple_echo import mcp

    async with client_session(mcp._mcp_server) as client:
        result = await client.call_tool("echo", {"text": "hello"})
        assert len(result.content) == 1
        content = result.content[0]
        assert isinstance(content, TextContent)
        assert content.text == "hello"


@pytest.mark.anyio
async def test_complex_inputs():
    """Test the complex inputs server"""
    from examples.fastmcp.complex_inputs import mcp

    async with client_session(mcp._mcp_server) as client:
        tank = {"shrimp": [{"name": "bob"}, {"name": "alice"}]}
        result = await client.call_tool(
            "name_shrimp", {"tank": tank, "extra_names": ["charlie"]}
        )
        assert len(result.content) == 3
        assert isinstance(result.content[0], TextContent)
        assert isinstance(result.content[1], TextContent)
        assert isinstance(result.content[2], TextContent)
        assert result.content[0].text == "bob"
        assert result.content[1].text == "alice"
        assert result.content[2].text == "charlie"


@pytest.mark.anyio
async def test_desktop():
    """Test the desktop server"""
    from pydantic import AnyUrl

    from examples.fastmcp.desktop import mcp

    async with client_session(mcp._mcp_server) as client:
        # Test the add function
        result = await client.call_tool("add", {"a": 1, "b": 2})
        assert len(result.content) == 1
        content = result.content[0]
        assert isinstance(content, TextContent)
        assert content.text == "3"

        # Test the desktop resource
        result = await client.read_resource(AnyUrl("dir://desktop"))
        assert len(result.contents) == 1
        content = result.contents[0]
        assert isinstance(content, TextContent)
        assert isinstance(content.text, str)
