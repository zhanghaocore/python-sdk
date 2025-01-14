# test_sse.py
import re
import time
import json
import anyio
import pytest
import httpx
from typing import AsyncGenerator
from starlette.applications import Starlette
from starlette.routing import Mount, Route

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import TextContent, Tool

# Test server implementation
class TestServer(Server):
    def __init__(self):
        super().__init__("test_server")

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
async def client(server) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create test client"""
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8765") as client:
        yield client

# Tests
@pytest.mark.anyio
async def test_sse_connection(client: httpx.AsyncClient):
    """Test SSE connection establishment"""
    async with anyio.create_task_group() as tg:
        async def connection_test():
            async with client.stream("GET", "/sse") as response:
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
async def test_message_exchange(client: httpx.AsyncClient):
    """Test full message exchange flow"""
    # Connect to SSE endpoint
    session_id = None
    endpoint_url = None

    async with client.stream("GET", "/sse") as sse_response:
        assert sse_response.status_code == 200

        # Get endpoint URL and session ID
        async for line in sse_response.aiter_lines():
            if line.startswith("data: "):
                endpoint_url = json.loads(line[6:])
                session_id = endpoint_url.split("session_id=")[1]
                break

        assert endpoint_url and session_id

        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test_client",
                    "version": "1.0"
                }
            }
        }

        response = await client.post(
            endpoint_url,
            json=init_request
        )
        assert response.status_code == 202

        # Get initialize response from SSE stream
        async for line in sse_response.aiter_lines():
            if line.startswith("event: message"):
                data_line = next(sse_response.aiter_lines())
                response = json.loads(data_line[6:])  # Strip "data: " prefix
                assert response["jsonrpc"] == "2.0"
                assert response["id"] == 1
                assert "result" in response
                break

@pytest.mark.anyio
async def test_invalid_session(client: httpx.AsyncClient):
    """Test sending message with invalid session ID"""
    response = await client.post(
        "/messages/?session_id=invalid",
        json={"jsonrpc": "2.0", "method": "ping"}
    )
    assert response.status_code == 400

@pytest.mark.anyio
async def test_connection_cleanup(server_app):
    """Test that resources are cleaned up when client disconnects"""
    sse = next(
        route.app for route in server_app.routes
        if isinstance(route, Mount) and route.path == "/messages/"
    ).transport

    async with httpx.AsyncClient(app=server_app, base_url="http://test") as client:
        # Connect and get session ID
        async with client.stream("GET", "/sse") as response:
            for line in response.iter_lines():
                if line.startswith("data: "):
                    endpoint_url = json.loads(line[6:])
                    session_id = endpoint_url.split("session_id=")[1]
                    break

            assert len(sse._read_stream_writers) == 1

        # After connection closes, writer should be cleaned up
        await anyio.sleep(0.1)  # Give cleanup a moment
        assert len(sse._read_stream_writers) == 0
