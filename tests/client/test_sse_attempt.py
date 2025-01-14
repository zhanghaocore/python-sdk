import anyio
import pytest
from starlette.applications import Starlette
from starlette.routing import Mount, Route
import httpx
from httpx import ReadTimeout, ASGITransport

from mcp.client.sse import sse_client
from mcp.server.sse import SseServerTransport
from mcp.types import JSONRPCMessage


@pytest.fixture
async def sse_transport():
    """Fixture that creates an SSE transport instance."""
    return SseServerTransport("/messages/")


@pytest.fixture
async def sse_app(sse_transport):
    """Fixture that creates a Starlette app with SSE endpoints."""
    async def handle_sse(request):
        """Handler for SSE connections."""
        async with sse_transport.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            client_to_server, server_to_client = streams
            async for message in client_to_server:
                # Echo messages back for testing
                await server_to_client.send(message)

    routes = [
        Route("/sse", endpoint=handle_sse),
        Mount("/messages", app=sse_transport.handle_post_message),
    ]

    return Starlette(routes=routes)


@pytest.fixture
async def test_client(sse_app):
    """Create a test client with ASGI transport."""
    async with httpx.AsyncClient(
        transport=ASGITransport(app=sse_app),
        base_url="http://testserver",
    ) as client:
        yield client


@pytest.mark.anyio
async def test_sse_connection(test_client):
    """Test basic SSE connection and message exchange."""
    async with sse_client(
        "http://testserver/sse",
        headers={"Host": "testserver"},
        timeout=5,
        client=test_client,
    ) as (read_stream, write_stream):
        # Send a test message
        test_message = JSONRPCMessage.model_validate({"jsonrpc": "2.0", "method": "test"})
        await write_stream.send(test_message)

        # Receive echoed message
        async with read_stream:
            message = await read_stream.__anext__()
            assert isinstance(message, JSONRPCMessage)
            assert message.model_dump() == test_message.model_dump()


@pytest.mark.anyio
async def test_sse_read_timeout(test_client):
    """Test that SSE client properly handles read timeouts."""
    with pytest.raises(ReadTimeout):
        async with sse_client(
            "http://testserver/sse",
            headers={"Host": "testserver"},
            timeout=5,
            sse_read_timeout=1,
            client=test_client,
        ) as (read_stream, write_stream):
            async with read_stream:
                # This should timeout since no messages are being sent
                await read_stream.__anext__()


@pytest.mark.anyio
async def test_sse_connection_error(test_client):
    """Test SSE client behavior with connection errors."""
    with pytest.raises(httpx.HTTPError):
        async with sse_client(
            "http://testserver/nonexistent",
            headers={"Host": "testserver"},
            timeout=5,
            client=test_client,
        ):
            pass  # Should not reach here


@pytest.mark.anyio
async def test_sse_multiple_messages(test_client):
    """Test sending and receiving multiple SSE messages."""
    async with sse_client(
        "http://testserver/sse",
        headers={"Host": "testserver"},
        timeout=5,
        client=test_client,
    ) as (read_stream, write_stream):
        # Send multiple test messages
        messages = [
            JSONRPCMessage.model_validate({"jsonrpc": "2.0", "method": f"test{i}"})
            for i in range(3)
        ]

        for msg in messages:
            await write_stream.send(msg)

        # Receive all echoed messages
        received = []
        async with read_stream:
            for _ in range(len(messages)):
                message = await read_stream.__anext__()
                assert isinstance(message, JSONRPCMessage)
                received.append(message)

        # Verify all messages were received in order
        for sent, received in zip(messages, received):
            assert sent.model_dump() == received.model_dump()