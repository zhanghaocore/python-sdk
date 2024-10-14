"""
This module provides simpler types to use with the server for managing prompts.
"""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

from mcp_python.types import Role, ServerCapabilities


@dataclass
class ImageContent:
    type: Literal["image"]
    data: str
    mime_type: str


@dataclass
class Message:
    role: Role
    content: str | ImageContent


@dataclass
class PromptResponse:
    messages: list[Message]
    desc: str | None = None


class InitializationOptions(BaseModel):
    server_name: str
    server_version: str
    capabilities: ServerCapabilities
