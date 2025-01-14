# test_sse.py
import re
import time
import json
import anyio
from pydantic import AnyUrl
from pydantic_core import Url
import pytest
import httpx
from typing import AsyncGenerator
from starlette.applications import Starlette
from starlette.routing import Mount, Route

from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import EmptyResult, InitializeResult, TextContent, TextResourceContents, Tool

SERVER_URL = "http://127.0.0.1:8765"
SERVER_SSE_URL = f"{SERVER_URL}/sse"

SERVER_NAME = "test_server_for_SSE"

# Test server implementation
class TestServer(Server):
    def __init__(self):
        super().__init__(SERVER_NAME)

        @self.read_resource()
        async def handle_read_resource(uri: AnyUrl) -> str | bytes:
            if uri.scheme == "foobar":
                return f"Read {uri.host}"
            # TODO: make this an error
            return "NOT FOUND"

        @self.list_tools()
        async def handle_list_tools():
            return [
                Tool(
                    name="test_tool",
                    description="A test tool",
                    inputSchema={"type": "object", "properties": {}}
                )
            ]

        @self.call_tool()
        async def handle_call_tool(name: str, args: dict):
            return [TextContent(type="text", text=f"Called {name}")]

import threading
import uvicorn
import pytest


# Test fixtures
@pytest.fixture
async def server_app()-> Starlette:
    """Create test Starlette app with SSE transport"""
    sse = SseServerTransport("/messages/")
    server = TestServer()

    async def handle_sse(request):
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await server.run(
                streams[0],
                streams[1],
                server.create_initialization_options()
            )

    app = Starlette(routes=[
        Route("/sse", endpoint=handle_sse),
        Mount("/messages/", app=sse.handle_post_message),
    ])

    return app

@pytest.fixture()
def server(server_app: Starlette):
    server = uvicorn.Server(config=uvicorn.Config(app=server_app, host="127.0.0.1", port=8765, log_level="error"))
    server_thread = threading.Thread( target=server.run, daemon=True )
    print('starting server')
    server_thread.start()
    # Give server time to start
    while not server.started:
        print('waiting for server to start')
        time.sleep(0.5)
    yield
    print('killing server')
    server_thread.join(timeout=0.1)

@pytest.fixture()
async def http_client(server) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create test client"""
    async with httpx.AsyncClient(base_url=SERVER_URL) as client:
        yield client

# Tests
@pytest.mark.anyio
async def test_raw_sse_connection(http_client: httpx.AsyncClient):
    """Test the SSE connection establishment simply with an HTTP client."""
    async with anyio.create_task_group() as tg:
        async def connection_test():
            async with http_client.stream("GET", "/sse") as response:
                assert response.status_code == 200
                assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

                line_number = 0
                async for line in response.aiter_lines():
                    if line_number == 0:
                        assert line == "event: endpoint"
                    elif line_number == 1:
                        assert line.startswith("data: /messages/?session_id=")
                    else:
                        return
                    line_number += 1

        # Add timeout to prevent test from hanging if it fails
        with anyio.fail_after(3):
            await connection_test()


@pytest.mark.anyio
async def test_sse_client_basic_connection(server):
    async with sse_client(SERVER_SSE_URL) as streams:
        async with ClientSession(*streams) as session:
            # Test initialization
            result = await session.initialize()
            assert isinstance(result, InitializeResult)
            assert result.serverInfo.name == SERVER_NAME

            # Test ping
            ping_result = await session.send_ping()
            assert isinstance(ping_result, EmptyResult)

@pytest.fixture
async def initialized_sse_client_session(server) -> AsyncGenerator[ClientSession, None]:
    async with sse_client(SERVER_SSE_URL) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            yield session

@pytest.mark.anyio
async def test_sse_client_request_and_response(initialized_sse_client_session: ClientSession):
    session = initialized_sse_client_session
    # TODO: expect raise
    await session.read_resource(uri=AnyUrl("xxx://will-not-work"))
    response = await session.read_resource(uri=AnyUrl("foobar://should-work"))
    assert len(response.contents) == 1
    assert isinstance(response.contents[0], TextResourceContents)
    assert response.contents[0].text == "Read should-work"
