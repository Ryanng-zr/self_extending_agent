from __future__ import annotations

from typing import Any
from pydantic import create_model
from self_extending_agent.models import GeneratedToolSpec
from self_extending_agent.sandbox.base import SandboxBackend
from self_extending_agent.tools.types import RegisteredTool


_TYPE_MAP = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
}


def registered_generated_tool(
    spec: GeneratedToolSpec,
    sandbox: SandboxBackend,
    timeout_seconds: int,
) -> RegisteredTool:
    def invoke(args: dict) -> dict:
        return sandbox.execute(
            spec.source,
            args,
            timeout_seconds,
        )
    return RegisteredTool(
        name=spec.name,
        description=spec.description,
        capabilities=spec.capabilities,
        input_schema=spec.inputs,
        function=invoke,
        generated=True,
        verified=True,
        version=1,
        source=spec.source,
    )


def to_langchain_tool(tool: RegisteredTool):
    from langchain_core.tools import StructuredTool
    fields = {
        name: (_TYPE_MAP.get(type_name, str), ...)
        for name, type_name in tool.input_schema.items()
    }
    ArgsModel = create_model(f"{tool.name.title()}Args", **fields)

    return StructuredTool.from_function(
        func=tool.function,
        name=tool.name,
        description=tool.description,
        args_schema=ArgsModel,
    )
