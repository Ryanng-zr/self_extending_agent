from __future__ import annotations

from typing import Iterable
from .types import RegisteredTool


class ToolRegistry:
    """
    Single source of truth for every tool the agent is permitted to use.

    The synthesis path receives the FULL catalogue. This is deliberate:
    synthesis is a fallback, never a shortcut around discovery.
    """

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, tool: RegisteredTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> RegisteredTool | None:
        return self._tools.get(name)

    def all(self) -> list[RegisteredTool]:
        return list(self._tools.values())

    def names(self) -> set[str]:
        return set(self._tools)

    def capabilities(self) -> set[str]:
        values: set[str] = set()
        for tool in self.all():
            values.update(c.lower() for c in tool.capabilities)
            values.update(a.lower() for a in tool.aliases)
        return values
    
    def execute(
        self,
        name: str,
        arguments: dict,
    ) -> dict:
        tool = self.get(name)

        try:
            output = tool.function(arguments)

        except Exception as exc:
            raise RuntimeError(
                f"Tool {name!r} failed during execution: {exc}"
            ) from exc

        if not isinstance(output, dict):
            raise ValueError(
                f"Tool {name!r} must return a dict, "
                f"got {type(output).__name__}."
            )

        return output
    
    def exact_capability_matches(self, capability: str) -> list[RegisteredTool]:
        target = capability.strip().lower()
        matches = []
        for tool in self.all():
            candidates = {
                *(c.strip().lower() for c in tool.capabilities),
                *(a.strip().lower() for a in tool.aliases),
            }
            if target in candidates:
                matches.append(tool)
        return matches

    def catalogue_text(self) -> str:
        if not self._tools:
            return "(no tools registered)"
        chunks = []
        for tool in self.all():
            chunks.append(
                f"- name: {tool.name}\n"
                f"  description: {tool.description}\n"
                f"  capabilities: {tool.capabilities}\n"
                f"  inputs: {tool.input_schema}\n"
                f"  generated: {tool.generated}\n"
                f"  verified: {tool.verified}"
            )
        return "\n".join(chunks)
