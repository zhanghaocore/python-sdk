import anyio
import pytest

from mcp_python.client.session import ClientSession
from mcp_python.server.session import ServerSession
from mcp_python.types import (
    ClientNotification,
    InitializedNotification,
    JSONRPCMessage,
)


@pytest.mark.anyio
async def test_server_session_initialize():
    server_to_client_send, server_to_client_receive = anyio.create_memory_object_stream(
        1, JSONRPCMessage
    )
    client_to_server_send, client_to_server_receive = anyio.create_memory_object_stream(
        1, JSONRPCMessage
    )

    async def run_client(client: ClientSession):
        async for message in client_session.incoming_messages:
            if isinstance(message, Exception):
                raise message

    received_initialized = False

    async def run_server():
        nonlocal received_initialized

        async with ServerSession(
            client_to_server_receive, server_to_client_send
        ) as server_session:
            async for message in server_session.incoming_messages:
                if isinstance(message, Exception):
                    raise message

                if isinstance(message, ClientNotification) and isinstance(
                    message.root, InitializedNotification
                ):
                    received_initialized = True
                    return

    try:
        async with (
            ClientSession(
                server_to_client_receive, client_to_server_send
            ) as client_session,
            anyio.create_task_group() as tg,
        ):
            tg.start_soon(run_client, client_session)
            tg.start_soon(run_server)

            await client_session.initialize()
    except anyio.ClosedResourceError:
        pass

    assert received_initialized
