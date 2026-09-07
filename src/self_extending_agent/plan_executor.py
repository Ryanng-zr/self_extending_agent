from typing import Any
from uuid import uuid4
from self_extending_agent.models import (
    ToolExecutionPlan,
    ToolExecutionRecord,
)

def validate_plan(
    plan: ToolExecutionPlan,
    registry,
) -> None:

    seen_ids: set[str] = set()

    for step in plan.steps:

        if step.id in seen_ids:
            raise ValueError(
                f"Duplicate step ID: {step.id}"
            )

        if step.tool not in registry.names():            
            raise ValueError(
                f"Unknown tool in plan: {step.tool}"
            )

        for value in step.arguments.values():

            if (
                isinstance(value, str)
                and value.startswith("$")
            ):
                referenced_step = (
                    value[1:]
                    .split(".", 1)[0]
                )

                if referenced_step not in seen_ids:
                    raise ValueError(
                        "Plan references a future "
                        f"or nonexistent step: {value}"
                    )

        seen_ids.add(step.id)

def _resolve_reference(
    value: Any,
    results: dict[str, dict],
) -> Any:

    if not isinstance(value, str):
        return value

    if not value.startswith("$"):
        return value

    reference = value[1:]

    parts = reference.split(".")

    step_id = parts[0]

    if step_id not in results:
        raise ValueError(
            f"Unknown plan step reference: {step_id}"
        )

    current: Any = results[step_id]

    for field in parts[1:]:
        if not isinstance(current, dict):
            raise ValueError(
                f"Cannot resolve reference: {value}"
            )

        if field not in current:
            raise ValueError(
                f"Field '{field}' does not exist "
                f"in output of '{step_id}'"
            )

        current = current[field]

    return current

def _resolve_arguments(
    arguments: dict[str, Any],
    results: dict[str, dict],
) -> dict[str, Any]:

    return {
        key: _resolve_reference(
            value,
            results,
        )
        for key, value in arguments.items()
    }

def execute_plan(
    plan: ToolExecutionPlan,
    registry,
) -> list[ToolExecutionRecord]:

    validate_plan(
        plan,
        registry,
    )

    step_results: dict[str, dict] = {}
    records: list[ToolExecutionRecord] = []

    for step in plan.steps:

        if step.tool not in registry.names():            
            raise ValueError(
                f"Execution plan references "
                f"unknown tool '{step.tool}'"
            )

        resolved_arguments = _resolve_arguments(
            step.arguments,
            step_results,
        )

        tool = registry.get(step.tool)

        output = registry.execute(
            step.tool,
            resolved_arguments,
        )

        if not isinstance(output, dict):
            raise ValueError(
                f"Tool '{step.tool}' must return a dict."
            )

        step_results[step.id] = output

        records.append(
            ToolExecutionRecord(
                execution_id=str(uuid4()),
                tool=tool.name,
                tool_version=tool.version,
                generated=tool.generated,
                verified=tool.verified,
                inputs=resolved_arguments,
                output=output,
            )
        )

    return records