from __future__ import annotations

import uuid
from typing import Any

from self_extending_agent.models import ToolExecutionRecord
from self_extending_agent.tools.registry import ToolRegistry
from self_extending_agent.dynamic_tools import to_langchain_tool


def execute_with_langchain_agent(
    model: str,
    user_request: str,
    registry: ToolRegistry,
) -> tuple[str, list[ToolExecutionRecord]]:
    """
    Run the normal agent only AFTER discovery/synthesis is complete.

    Every tool is wrapped to capture immutable provenance records. The final
    answer is returned by the agent, but workflow.py later produces a second
    evidence-grounded final answer from the captured records.
    """
    from langchain.agents import create_agent

    records: list[ToolExecutionRecord] = []
    langchain_tools = []

    for registered in registry.all():
        original = registered.function

        def make_traced(tool, fn):
            def traced(**kwargs):
                output = fn(**kwargs)
                records.append(
                    ToolExecutionRecord(
                        tool=tool.name,
                        tool_version=tool.version,
                        generated=tool.generated,
                        verified=tool.verified,
                        inputs=kwargs,
                        output=output,
                        execution_id=str(uuid.uuid4()),
                    )
                )
                return output
            return traced

        traced_registered = type(registered)(
            name=registered.name,
            description=registered.description,
            capabilities=registered.capabilities,
            input_schema=registered.input_schema,
            function=make_traced(registered, original),
            generated=registered.generated,
            verified=registered.verified,
            version=registered.version,
            source=registered.source,
            aliases=registered.aliases,
        )
        langchain_tools.append(to_langchain_tool(traced_registered))

    agent = create_agent(
        model=model,
        tools=langchain_tools,
        system_prompt="""
You are the execution agent. The tool registry has already passed through
mandatory discovery and, where necessary, verified tool synthesis.

You MUST use tools for any source-data retrieval or calculation that can be
performed by a tool. Never invent coordinates, database values, or computed
results. Compose tools when needed. If a tool fails or data is unavailable,
say so rather than guessing.
""",
    )
    result = agent.invoke(
        {"messages": [{"role": "user", "content": user_request}]}
    )
    message = result["messages"][-1]

    text_parts = [
        block["text"]
        for block in message.content_blocks
        if block.get("type") == "text"
    ]

    return "\n".join(text_parts), records
