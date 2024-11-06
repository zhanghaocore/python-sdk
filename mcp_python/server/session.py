from enum import Enum
from typing import Any

import anyio
import anyio.lowlevel
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from pydantic import AnyUrl

from mcp_python.server.types import InitializationOptions
from mcp_python.shared.session import (
    BaseSession,
    RequestResponder,
)
from mcp_python.types import (
    ListRootsResult, LATEST_PROTOCOL_VERSION,
    ClientNotification,
    ClientRequest,
    CreateMessageResult,
    EmptyResult,
    Implementation,
    IncludeContext,
    InitializedNotification,
    InitializeRequest,
    InitializeResult,
    JSONRPCMessage,
    LoggingLevel,
    SamplingMessage,
    ServerNotification,
    ServerRequest,
    ServerResult,
    ResourceListChangedNotification,
    ToolListChangedNotification,
    PromptListChangedNotification,
    ModelPreferences,
)


class InitializationState(Enum):
    NotInitialized = 1
    Initializing = 2
    Initialized = 3


class ServerSession(
    BaseSession[
        ServerRequest,
        ServerNotification,
        ServerResult,
        ClientRequest,
        ClientNotification,
    ]
):
    _initialized: InitializationState = InitializationState.NotInitialized

    def __init__(
        self,
        read_stream: MemoryObjectReceiveStream[JSONRPCMessage | Exception],
        write_stream: MemoryObjectSendStream[JSONRPCMessage],
        init_options: InitializationOptions,
    ) -> None:
        super().__init__(read_stream, write_stream, ClientRequest, ClientNotification)
        self._initialization_state = InitializationState.NotInitialized
        self._init_options = init_options

    async def _received_request(
        self, responder: RequestResponder[ClientRequest, ServerResult]
    ):
        match responder.request.root:
            case InitializeRequest():
                self._initialization_state = InitializationState.Initializing
                await responder.respond(
                    ServerResult(
                        InitializeResult(
                            protocolVersion=LATEST_PROTOCOL_VERSION,
                            capabilities=self._init_options.capabilities,
                            serverInfo=Implementation(
                                name=self._init_options.server_name,
                                version=self._init_options.server_version,
                            ),
                        )
                    )
                )
            case _:
                if self._initialization_state != InitializationState.Initialized:
                    raise RuntimeError(
                        "Received request before initialization was complete"
                    )

    async def _received_notification(self, notification: ClientNotification) -> None:
        # Need this to avoid ASYNC910
        await anyio.lowlevel.checkpoint()
        match notification.root:
            case InitializedNotification():
                self._initialization_state = InitializationState.Initialized
            case _:
                if self._initialization_state != InitializationState.Initialized:
                    raise RuntimeError(
                        "Received notification before initialization was complete"
                    )

    async def send_log_message(
        self, level: LoggingLevel, data: Any, logger: str | None = None
    ) -> None:
        """Send a log message notification."""
        from mcp_python.types import (
            LoggingMessageNotification,
            LoggingMessageNotificationParams,
        )

        await self.send_notification(
            ServerNotification(
                LoggingMessageNotification(
                    method="notifications/message",
                    params=LoggingMessageNotificationParams(
                        level=level,
                        data=data,
                        logger=logger,
                    ),
                )
            )
        )

    async def send_resource_updated(self, uri: AnyUrl) -> None:
        """Send a resource updated notification."""
        from mcp_python.types import (
            ResourceUpdatedNotification,
            ResourceUpdatedNotificationParams,
        )

        await self.send_notification(
            ServerNotification(
                ResourceUpdatedNotification(
                    method="notifications/resources/updated",
                    params=ResourceUpdatedNotificationParams(uri=uri),
                )
            )
        )

    async def create_message(
        self,
        messages: list[SamplingMessage],
        *,
        max_tokens: int,
        system_prompt: str | None = None,
        include_context: IncludeContext | None = None,
        temperature: float | None = None,
        stop_sequences: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        model_preferences: ModelPreferences | None = None,
    ) -> CreateMessageResult:
        """Send a sampling/create_message request."""
        from mcp_python.types import (
            CreateMessageRequest,
            CreateMessageRequestParams,
        )

        return await self.send_request(
            ServerRequest(
                CreateMessageRequest(
                    method="sampling/createMessage",
                    params=CreateMessageRequestParams(
                        messages=messages,
                        systemPrompt=system_prompt,
                        includeContext=include_context,
                        temperature=temperature,
                        maxTokens=max_tokens,
                        stopSequences=stop_sequences,
                        metadata=metadata,
                        modelPreferences=model_preferences,
                    ),
                )
            ),
            CreateMessageResult,
        )

    async def list_roots(self) -> ListRootsResult:
        """Send a roots/list request."""
        from mcp_python.types import ListRootsRequest

        return await self.send_request(
            ServerRequest(
                ListRootsRequest(
                    method="roots/list",
                )
            ),
            ListRootsResult,
        )

    async def send_ping(self) -> EmptyResult:
        """Send a ping request."""
        from mcp_python.types import PingRequest

        return await self.send_request(
            ServerRequest(
                PingRequest(
                    method="ping",
                )
            ),
            EmptyResult,
        )

    async def send_progress_notification(
        self, progress_token: str | int, progress: float, total: float | None = None
    ) -> None:
        """Send a progress notification."""
        from mcp_python.types import ProgressNotification, ProgressNotificationParams

        await self.send_notification(
            ServerNotification(
                ProgressNotification(
                    method="notifications/progress",
                    params=ProgressNotificationParams(
                        progressToken=progress_token,
                        progress=progress,
                        total=total,
                    ),
                )
            )
        )

    async def send_resource_list_changed(self) -> None:
        """Send a resource list changed notification."""
        await self.send_notification(
            ServerNotification(
                ResourceListChangedNotification(
                    method="notifications/resources/list_changed",
                )
            )
        )

    async def send_tool_list_changed(self) -> None:
        """Send a tool list changed notification."""
        await self.send_notification(
            ServerNotification(
                ToolListChangedNotification(
                    method="notifications/tools/list_changed",
                )
            )
        )

    async def send_prompt_list_changed(self) -> None:
        """Send a prompt list changed notification."""
        await self.send_notification(
            ServerNotification(
                PromptListChangedNotification(
                    method="notifications/prompts/list_changed",
                )
            )
        )
