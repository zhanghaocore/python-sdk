"""
This module provides simpler types to use with the server for managing prompts and tools.
"""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

from mcp_python.types import Role, ServerCapabilities, TextResourceContents, BlobResourceContents


@dataclass
class ImageContent:
    type: Literal["image"]
    data: str
    mime_type: str


@dataclass
class EmbeddedResource:
    resource: TextResourceContents | BlobResourceContents


@dataclass
class Message:
    role: Role
    content: str | ImageContent | EmbeddedResource


@dataclass
class PromptResponse:
    messages: list[Message]
    desc: str | None = None


class InitializationOptions(BaseModel):
    server_name: str
    server_version: str
    capabilities: ServerCapabilities
