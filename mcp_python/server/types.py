"""
This module provides simpler types to use with the server for managing prompts.
"""

from dataclasses import dataclass
from typing import Literal

from mcp_python.types import Role


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
