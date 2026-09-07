from __future__ import annotations

from pathlib import Path

from self_extending_agent.config import settings
from self_extending_agent.dynamic_tools import registered_generated_tool
from self_extending_agent.generated_store import GeneratedToolStore
from self_extending_agent.llm.base import WorkflowModel
from self_extending_agent.models import (
    DiscoveryDecision,
    WorkflowResult,
)
from self_extending_agent.plan_executor import execute_plan
from self_extending_agent.sandbox.base import SandboxBackend
from self_extending_agent.tools.registry import ToolRegistry


def _validate_discovery(
    decision: DiscoveryDecision,
    registry: ToolRegistry,
) -> None:
    invalid = set(decision.selected_tools) - registry.names()

    if invalid:
        raise RuntimeError(
            "Discovery selected unregistered tools: "
            + ", ".join(sorted(invalid))
        )


def run_workflow(
    *,
    user_request: str,
    registry: ToolRegistry,
    model_adapter: WorkflowModel,
    sandbox: SandboxBackend,
    mode: str,
    langchain_model_name: str,
    generated_root: Path,
    max_attempts: int | None = None,
    timeout_seconds: int | None = None,
) -> WorkflowResult:

    max_attempts = (
        max_attempts
        or settings.max_tool_generation_attempts
    )

    timeout_seconds = (
        timeout_seconds
        or settings.tool_execution_timeout_seconds
    )

    store = GeneratedToolStore(generated_root)

    trace: list[str] = []
    generated_names: list[str] = []

    # ---------------------------------------------------------
    # 1. Requirement analysis
    # ---------------------------------------------------------

    catalogue = registry.catalogue_text()

    requirement = model_adapter.analyze_requirements(
        user_request,
        catalogue,
    )

    trace.append(
        f"Requirement analysis: "
        f"{requirement.required_capabilities}"
    )

    # ---------------------------------------------------------
    # 2. Mandatory discovery
    # ---------------------------------------------------------

    discovery = model_adapter.discover_tools(
        user_request,
        requirement,
        catalogue,
    )

    _validate_discovery(
        discovery,
        registry,
    )

    trace.append(
        f"Discovery: "
        f"selected={discovery.selected_tools}, "
        f"missing={discovery.missing_capabilities}"
    )

    # ---------------------------------------------------------
    # 3. Synthesize ONLY missing capabilities
    # ---------------------------------------------------------

    for missing in list(
        discovery.missing_capabilities
    ):

        failure_feedback = ""
        verified = False

        for attempt in range(
            1,
            max_attempts + 1,
        ):

            trace.append(
                f"Synthesis attempt "
                f"{attempt}/{max_attempts} "
                f"for: {missing}"
            )

            spec = model_adapter.synthesize_tool(
                user_request=user_request,
                missing_capability=missing,
                catalogue=registry.catalogue_text(),
                failure_feedback=failure_feedback,
            )

            # Do not overwrite an existing tool.
            if spec.name in registry.names():

                failure_feedback = (
                    f"Rejected: {spec.name!r} "
                    f"already exists in the registry."
                )

                trace.append(
                    failure_feedback
                )

                continue

            # Verify generated code before registration.
            verification = sandbox.verify(
                spec.source,
                [
                    test.model_dump()
                    for test
                    in spec.generated_tests
                ],
                timeout_seconds,
            )

            trace.append(
                f"Verification for {spec.name}: "
                f"{'PASS' if verification.passed else 'FAIL'}"
            )

            if not verification.passed:

                trace.append(
                    "Verification failure details:\n"
                    f"Reasons: "
                    f"{verification.reasons}\n"
                    f"STDOUT:\n"
                    f"{verification.stdout}\n"
                    f"STDERR:\n"
                    f"{verification.stderr}"
                )

                failure_feedback = (
                    verification.stdout
                    + "\n"
                    + verification.stderr
                    + "\n"
                    + "; ".join(
                        verification.reasons
                    )
                ).strip()

                continue

            # Persist only after verification.
            manifest = store.persist_verified(
                spec
            )

            # Register generated tool into current registry.
            registry.register(
                registered_generated_tool(
                    spec,
                    sandbox,
                    timeout_seconds,
                )
            )

            generated_names.append(
                spec.name
            )

            trace.append(
                "Registered verified generated "
                f"tool: {manifest.name}"
            )

            verified = True

            break

        # Could not synthesize a valid tool.
        if not verified:

            answer = (
                "I could not create a verified "
                "tool for the required capability "
                f"{missing!r} after "
                f"{max_attempts} attempts, "
                "so I will not fabricate an answer."
            )

            return WorkflowResult(
                answer=answer,
                requirement=requirement,
                discovery=discovery,
                generated_tools=generated_names,
                evidence=[],
                trace=trace,
            )

    # ---------------------------------------------------------
    # 4. Rediscover using UPDATED registry
    # ---------------------------------------------------------

    discovery = model_adapter.discover_tools(
        user_request,
        requirement,
        registry.catalogue_text(),
    )

    _validate_discovery(
        discovery,
        registry,
    )

    trace.append(
        "Post-registration rediscovery: "
        f"selected={discovery.selected_tools}, "
        f"missing={discovery.missing_capabilities}"
    )

    # Stop if something is still missing.
    if discovery.missing_capabilities:

        return WorkflowResult(
            answer=(
                "The workflow still has unresolved "
                "capabilities after tool synthesis, "
                "so it will not guess."
            ),
            requirement=requirement,
            discovery=discovery,
            generated_tools=generated_names,
            evidence=[],
            trace=trace,
        )

    # ---------------------------------------------------------
    # 5. NEW: Create an explicit execution plan
    # ---------------------------------------------------------

    plan = model_adapter.create_execution_plan(
        user_request=user_request,
        available_tools=registry.catalogue_text(),
    )

    trace.append(
        "Execution plan: "
        + " -> ".join(
            step.tool
            for step in plan.steps
        )
    )

    for index, step in enumerate(
        plan.steps,
        start=1,
    ):
        trace.append(
            f"Plan step {index}: "
            f"id={step.id}, "
            f"tool={step.tool}, "
            f"arguments={step.arguments}"
        )

    # ---------------------------------------------------------
    # 6. NEW: Execute plan deterministically
    # ---------------------------------------------------------

    evidence = execute_plan(
        plan=plan,
        registry=registry,
    )

    trace.append(
        f"Executed "
        f"{len(evidence)} "
        f"planned tool calls."
    )

    # ---------------------------------------------------------
    # 7. Evidence-grounded final answer
    # ---------------------------------------------------------

    answer = model_adapter.final_answer(
        user_request,
        evidence,
    )

    trace.append(
        "Generated final answer from "
        "verified tool evidence only."
    )

    return WorkflowResult(
        answer=answer,
        requirement=requirement,
        discovery=discovery,
        generated_tools=generated_names,
        evidence=evidence,
        trace=trace,
    )