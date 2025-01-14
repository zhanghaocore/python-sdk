# test_sse.py
import re
import time
import json
import anyio
import threading
import uvicorn
import pytest
from pydantic import AnyUrl
from pydantic_core import Url
import pytest
import httpx
from typing import AsyncGenerator
from starlette.applications import Starlette
from starlette.routing import Mount, Route

from mcp.shared.exceptions import McpError
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import EmptyResult, ErrorData, InitializeResult, TextContent, TextResourceContents, Tool

SERVER_NAME = "test_server_for_SSE"

@pytest.fixture
def server_port() -> int:
    import socket

    s = socket.socket()
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port

@pytest.fixture
def server_url(server_port: int) -> str:
    return f"http://127.0.0.1:{server_port}"

# Test server implementation
class TestServer(Server):
    def __init__(self):
        super().__init__(SERVER_NAME)

        @self.read_resource()
        async def handle_read_resource(uri: AnyUrl) -> str | bytes:
            if uri.scheme == "foobar":
                return f"Read {uri.host}"
            # TODO: make this an error
            raise McpError(error=ErrorData(code=404, message="OOPS! no resource with that URI was found"))

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
def server(server_app: Starlette, server_port: int):
    server = uvicorn.Server(config=uvicorn.Config(app=server_app, host="127.0.0.1", port=server_port, log_level="error"))
    server_thread = threading.Thread( target=server.run, daemon=True )
    print(f'starting server on {server_port}')
    server_thread.start()
    # Give server time to start
    while not server.started:
        print('waiting for server to start')
        time.sleep(0.5)
    yield
    print('killing server')
    server_thread.join(timeout=0.1)

@pytest.fixture()
async def http_client(server, server_url) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create test client"""
    async with httpx.AsyncClient(base_url=server_url) as client:
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
async def test_sse_client_basic_connection(server, server_url):
    async with sse_client(server_url + "/sse") as streams:
        async with ClientSession(*streams) as session:
            # Test initialization
            result = await session.initialize()
            assert isinstance(result, InitializeResult)
            assert result.serverInfo.name == SERVER_NAME

            # Test ping
            ping_result = await session.send_ping()
            assert isinstance(ping_result, EmptyResult)

@pytest.fixture
async def initialized_sse_client_session(server, server_url: str) -> AsyncGenerator[ClientSession, None]:
    async with sse_client(server_url + "/sse") as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            yield session

@pytest.mark.anyio
async def test_sse_client_happy_request_and_response(initialized_sse_client_session: ClientSession):
    session = initialized_sse_client_session
    response = await session.read_resource(uri=AnyUrl("foobar://should-work"))
    assert len(response.contents) == 1
    assert isinstance(response.contents[0], TextResourceContents)
    assert response.contents[0].text == "Read should-work"

@pytest.mark.anyio
async def test_sse_client_exception_handling(initialized_sse_client_session: ClientSession):
    session = initialized_sse_client_session
    with pytest.raises(McpError, match="OOPS! no resource with that URI was found"):
        await session.read_resource(uri=AnyUrl("xxx://will-not-work"))
