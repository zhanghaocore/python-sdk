from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from mcp.shared.session import BaseSession
from mcp.types import RequestId, RequestParams

SessionT = TypeVar("SessionT", bound=BaseSession)


@dataclass
class RequestContext(Generic[SessionT]):
    request_id: RequestId
    meta: RequestParams.Meta | None
    session: SessionT
    lifespan_context: Any
