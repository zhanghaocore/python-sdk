from datetime import timedelta

from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from pydantic import AnyUrl, FileUrl

from mcp_python.shared.session import BaseSession
from mcp_python.shared.version import SUPPORTED_PROTOCOL_VERSIONS
from mcp_python.types import (
    LATEST_PROTOCOL_VERSION,
    CallToolResult,
    ClientCapabilities,
    ClientNotification,
    ClientRequest,
    ClientResult,
    CompleteResult,
    EmptyResult,
    GetPromptResult,
    Implementation,
    InitializedNotification,
    InitializeResult,
    JSONRPCMessage,
    ListPromptsResult,
    ListResourcesResult,
    ListRootsResult,
    ListToolsResult,
    LoggingLevel,
    PromptReference,
    ReadResourceResult,
    ResourceReference,
    ServerNotification,
    ServerRequest,
)


class ClientSession(
    BaseSession[
        ClientRequest,
        ClientNotification,
        ClientResult,
        ServerRequest,
        ServerNotification,
    ]
):
    def __init__(
        self,
        read_stream: MemoryObjectReceiveStream[JSONRPCMessage | Exception],
        write_stream: MemoryObjectSendStream[JSONRPCMessage],
        read_timeout_seconds: timedelta | None = None,
    ) -> None:
        super().__init__(
            read_stream,
            write_stream,
            ServerRequest,
            ServerNotification,
            read_timeout_seconds=read_timeout_seconds,
        )

    async def initialize(self) -> InitializeResult:
        from mcp_python.types import (
            InitializeRequest,
            InitializeRequestParams,
        )

        result = await self.send_request(
            ClientRequest(
                InitializeRequest(
                    method="initialize",
                    params=InitializeRequestParams(
                        protocolVersion=LATEST_PROTOCOL_VERSION,
                        capabilities=ClientCapabilities(
                            sampling=None,
                            experimental=None,
                            roots={
                                # TODO: Should this be based on whether we _will_ send notifications, or only whether they're supported?
                                "listChanged": True
                            }
                        ),
                        clientInfo=Implementation(name="mcp_python", version="0.1.0"),
                    ),
                )
            ),
            InitializeResult,
        )

        if result.protocolVersion not in SUPPORTED_PROTOCOL_VERSIONS:
            raise RuntimeError(
                "Unsupported protocol version from the server: "
                f"{result.protocolVersion}"
            )

        await self.send_notification(
            ClientNotification(
                InitializedNotification(method="notifications/initialized")
            )
        )

        return result

    async def send_ping(self) -> EmptyResult:
        """Send a ping request."""
        from mcp_python.types import PingRequest

        return await self.send_request(
            ClientRequest(
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
        from mcp_python.types import (
            ProgressNotification,
            ProgressNotificationParams,
        )

        await self.send_notification(
            ClientNotification(
                ProgressNotification(
                    method="notifications/progress",
                    params=ProgressNotificationParams(
                        progressToken=progress_token,
                        progress=progress,
                        total=total,
                    ),
                ),
            )
        )

    async def set_logging_level(self, level: LoggingLevel) -> EmptyResult:
        """Send a logging/setLevel request."""
        from mcp_python.types import (
            SetLevelRequest,
            SetLevelRequestParams,
        )

        return await self.send_request(
            ClientRequest(
                SetLevelRequest(
                    method="logging/setLevel",
                    params=SetLevelRequestParams(level=level),
                )
            ),
            EmptyResult,
        )

    async def list_resources(self) -> ListResourcesResult:
        """Send a resources/list request."""
        from mcp_python.types import (
            ListResourcesRequest,
        )

        return await self.send_request(
            ClientRequest(
                ListResourcesRequest(
                    method="resources/list",
                )
            ),
            ListResourcesResult,
        )

    async def read_resource(self, uri: AnyUrl) -> ReadResourceResult:
        """Send a resources/read request."""
        from mcp_python.types import (
            ReadResourceRequest,
            ReadResourceRequestParams,
        )

        return await self.send_request(
            ClientRequest(
                ReadResourceRequest(
                    method="resources/read",
                    params=ReadResourceRequestParams(uri=uri),
                )
            ),
            ReadResourceResult,
        )

    async def subscribe_resource(self, uri: AnyUrl) -> EmptyResult:
        """Send a resources/subscribe request."""
        from mcp_python.types import (
            SubscribeRequest,
            SubscribeRequestParams,
        )

        return await self.send_request(
            ClientRequest(
                SubscribeRequest(
                    method="resources/subscribe",
                    params=SubscribeRequestParams(uri=uri),
                )
            ),
            EmptyResult,
        )

    async def unsubscribe_resource(self, uri: AnyUrl) -> EmptyResult:
        """Send a resources/unsubscribe request."""
        from mcp_python.types import (
            UnsubscribeRequest,
            UnsubscribeRequestParams,
        )

        return await self.send_request(
            ClientRequest(
                UnsubscribeRequest(
                    method="resources/unsubscribe",
                    params=UnsubscribeRequestParams(uri=uri),
                )
            ),
            EmptyResult,
        )

    async def call_tool(
        self, name: str, arguments: dict | None = None
    ) -> CallToolResult:
        """Send a tools/call request."""
        from mcp_python.types import (
            CallToolRequest,
            CallToolRequestParams,
        )

        return await self.send_request(
            ClientRequest(
                CallToolRequest(
                    method="tools/call",
                    params=CallToolRequestParams(name=name, arguments=arguments),
                )
            ),
            CallToolResult,
        )

    async def list_prompts(self) -> ListPromptsResult:
        """Send a prompts/list request."""
        from mcp_python.types import ListPromptsRequest

        return await self.send_request(
            ClientRequest(
                ListPromptsRequest(
                    method="prompts/list",
                )
            ),
            ListPromptsResult,
        )

    async def get_prompt(self, name: str, arguments: dict[str, str] | None = None) -> GetPromptResult:
        """Send a prompts/get request."""
        from mcp_python.types import GetPromptRequest, GetPromptRequestParams

        return await self.send_request(
            ClientRequest(
                GetPromptRequest(
                    method="prompts/get",
                    params=GetPromptRequestParams(name=name, arguments=arguments),
                )
            ),
            GetPromptResult,
        )

    async def complete(self, ref: ResourceReference | PromptReference, argument: dict) -> CompleteResult:
        """Send a completion/complete request."""
        from mcp_python.types import CompleteRequest, CompleteRequestParams, CompletionArgument

        return await self.send_request(
            ClientRequest(
                CompleteRequest(
                    method="completion/complete",
                    params=CompleteRequestParams(
                        ref=ref,
                        argument=CompletionArgument(**argument),
                    ),
                )
            ),
            CompleteResult,
        )

    async def list_tools(self) -> ListToolsResult:
        """Send a tools/list request."""
        from mcp_python.types import ListToolsRequest

        return await self.send_request(
            ClientRequest(
                ListToolsRequest(
                    method="tools/list",
                )
            ),
            ListToolsResult,
        )

    async def send_roots_list_changed(self) -> None:
        """Send a roots/list_changed notification."""
        from mcp_python.types import RootsListChangedNotification

        await self.send_notification(
            ClientNotification(
                RootsListChangedNotification(
                    method="notifications/roots/list_changed",
                )
            )
        )
