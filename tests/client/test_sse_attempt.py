import anyio
import asyncio
import pytest
from starlette.applications import Starlette
from starlette.routing import Mount, Route
import httpx
from httpx import ReadTimeout, ASGITransport
from starlette.responses import Response
from sse_starlette.sse import EventSourceResponse

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
        async def event_generator():
            try:
                async with sse_transport.connect_sse(
                    request.scope, request.receive, request._send
                ) as streams:
                    client_to_server, server_to_client = streams
                    # Send initial connection event
                    yield {
                        "event": "endpoint",
                        "data": "/messages",
                    }

                    # Process messages
                    async with anyio.create_task_group() as tg:
                        try:
                            async for message in client_to_server:
                                if isinstance(message, Exception):
                                    break
                                yield {
                                    "event": "message",
                                    "data": message.model_dump_json(),
                                }
                        except (asyncio.CancelledError, GeneratorExit):
                            print('cancelled')
                            return
                        except Exception as e:
                            print("unhandled exception:", e)
                            return
            except Exception:
                # Log any unexpected errors but allow connection to close gracefully
                pass

        return EventSourceResponse(event_generator())

    routes = [
        Route("/sse", endpoint=handle_sse),
        Mount("/messages", app=sse_transport.handle_post_message),
    ]

    return Starlette(routes=routes)


@pytest.fixture
async def test_client(sse_app):
    """Create a test client with ASGI transport."""
    transport = ASGITransport(app=sse_app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
        timeout=10.0,
    ) as client:
        yield client


@pytest.mark.anyio
async def test_sse_connection(test_client):
    """Test basic SSE connection and message exchange."""
    async with anyio.create_task_group() as tg:
        try:
            async with sse_client(
                "http://testserver/sse",
                headers={"Host": "testserver"},
                timeout=5,
                sse_read_timeout=5,
                client=test_client,
            ) as (read_stream, write_stream):
                # First get the initial endpoint message
                async with read_stream:
                    init_message = await read_stream.__anext__()
                    assert isinstance(init_message, JSONRPCMessage)

                # Send a test message
                test_message = JSONRPCMessage.model_validate({"jsonrpc": "2.0", "method": "test"})
                await write_stream.send(test_message)

                # Receive echoed message
                async with read_stream:
                    message = await read_stream.__anext__()
                    assert isinstance(message, JSONRPCMessage)
                    assert message.model_dump() == test_message.model_dump()

                # Explicitly close streams
                await write_stream.aclose()
                await read_stream.aclose()
        except Exception as e:
            pytest.fail(f"Test failed with error: {str(e)}")


# @pytest.mark.anyio
# async def test_sse_read_timeout(test_client):
#     """Test that SSE client properly handles read timeouts."""
#     with pytest.raises(ReadTimeout):
#         async with sse_client(
#             "http://testserver/sse",
#             headers={"Host": "testserver"},
#             timeout=5,
#             sse_read_timeout=2,
#             client=test_client,
#         ) as (read_stream, write_stream):
#             async with read_stream:
#                 # This should timeout since no messages are being sent
#                 await read_stream.__anext__()


# @pytest.mark.anyio
# async def test_sse_connection_error(test_client):
#     """Test SSE client behavior with connection errors."""
#     with pytest.raises(httpx.HTTPError):
#         async with sse_client(
#             "http://testserver/nonexistent",
#             headers={"Host": "testserver"},
#             timeout=5,
#             client=test_client,
#         ):
#             pass  # Should not reach here


# @pytest.mark.anyio
# async def test_sse_multiple_messages(test_client):
#     """Test sending and receiving multiple SSE messages."""
#     async with sse_client(
#         "http://testserver/sse",
#         headers={"Host": "testserver"},
#         timeout=5,
#         sse_read_timeout=5,
#         client=test_client,
#     ) as (read_stream, write_stream):
#         # Send multiple test messages
#         messages = [
#             JSONRPCMessage.model_validate({"jsonrpc": "2.0", "method": f"test{i}"})
#             for i in range(3)
#         ]

#         for msg in messages:
#             await write_stream.send(msg)

#         # Receive all echoed messages
#         received = []
#         async with read_stream:
#             for _ in range(len(messages)):
#                 message = await read_stream.__anext__()
#                 assert isinstance(message, JSONRPCMessage)
#                 received.append(message)

#         # Verify all messages were received in order
#         for sent, received in zip(messages, received):
#             assert sent.model_dump() == received.model_dump()
