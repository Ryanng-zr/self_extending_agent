from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class RegisteredTool:
    name: str
    description: str
    capabilities: list[str]
    input_schema: dict[str, str]
    function: Callable[..., Any]
    generated: bool = False
    verified: bool = True
    version: int = 1
    source: str | None = None
    aliases: list[str] = field(default_factory=list)
