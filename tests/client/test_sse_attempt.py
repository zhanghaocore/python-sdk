import pytest
import anyio
from starlette.applications import Starlette
from starlette.routing import Mount, Route
import uvicorn
from mcp.client.sse import sse_client
from exceptiongroup import ExceptionGroup
import asyncio
import httpx
from httpx import ReadTimeout

from mcp.server.sse import SseServerTransport

@pytest.fixture
async def sse_server():

    # Create an SSE transport at an endpoint
    sse = SseServerTransport("/messages/")

    # Create Starlette routes for SSE and message handling
    routes = [
        Route("/sse", endpoint=handle_sse),
        Mount("/messages/", app=sse.handle_post_message),
    ]
    #
    # Create and run Starlette app
    app = Starlette(routes=routes)

    # Define handler functions
    async def handle_sse(request):
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await app.run(
                streams[0], streams[1], app.create_initialization_options()
            )

    uvicorn.run(app, host="127.0.0.1", port=34891)

    async def sse_handler(request):
        response = httpx.Response(200, content_type="text/event-stream")
        response.send_headers()
        response.write("data: test\n\n")
        await response.aclose()

    async with httpx.AsyncServer(sse_handler) as server:
        yield server.url


@pytest.fixture
async def sse_client():
    async with sse_client("http://test/sse") as (read_stream, write_stream):
        async with read_stream:
            async for message in read_stream:
                if isinstance(message, Exception):
                    raise message

    return read_stream, write_stream

@pytest.mark.anyio
async def test_sse_happy_path(monkeypatch):
    # Mock httpx.AsyncClient to return our mock response
    monkeypatch.setattr(httpx, "AsyncClient", MockClient)

    with pytest.raises(ReadTimeout) as exc_info:
        async with sse_client(
            "http://test/sse",
            timeout=5,  # Connection timeout - make this longer
            sse_read_timeout=1  # Read timeout - this should trigger
        ) as (read_stream, write_stream):
            async with read_stream:
                async for message in read_stream:
                    if isinstance(message, Exception):
                        raise message

    error = exc_info.value
    assert isinstance(error, ReadTimeout)
    assert str(error) == "Read timeout"

@pytest.mark.anyio
async def test_sse_read_timeouts(monkeypatch):
    """Test that the SSE client properly handles read timeouts between SSE messages."""
