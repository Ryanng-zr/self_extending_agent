from pathlib import Path

from self_extending_agent.llm.demo import DemoWorkflowModel
from self_extending_agent.sandbox.local import LocalSubprocessSandbox
from self_extending_agent.tools.builtin import build_builtin_registry
from self_extending_agent.workflow import run_workflow


def test_tool_is_synthesized_verified_registered_and_used(tmp_path: Path):
    registry = build_builtin_registry()

    assert registry.get("calculate_geographic_distance") is None

    result = run_workflow(
        user_request="How far is Location A from Location B?",
        registry=registry,
        model_adapter=DemoWorkflowModel(),
        sandbox=LocalSubprocessSandbox(),
        mode="demo",
        langchain_model_name="unused",
        generated_root=tmp_path / "generated_tools",
        max_attempts=3,
        timeout_seconds=5,
    )

    assert "calculate_geographic_distance" in result.generated_tools
    assert registry.get("calculate_geographic_distance") is not None
    assert registry.get("calculate_geographic_distance").verified is True

    distance_records = [
        r for r in result.evidence
        if r.tool == "calculate_geographic_distance"
    ]
    assert len(distance_records) == 1
    assert distance_records[0].output["distance_km"] > 0
    assert "verified tool result" in result.answer.lower()


def test_generated_tool_is_persisted_only_after_verification(tmp_path: Path):
    registry = build_builtin_registry()

    result = run_workflow(
        user_request="How far is Alpha Base from Bravo Base?",
        registry=registry,
        model_adapter=DemoWorkflowModel(),
        sandbox=LocalSubprocessSandbox(),
        mode="demo",
        langchain_model_name="unused",
        generated_root=tmp_path / "generated_tools",
        max_attempts=3,
        timeout_seconds=5,
    )

    folder = tmp_path / "generated_tools" / "calculate_geographic_distance"
    assert (folder / "tool.py").exists()
    assert (folder / "manifest.json").exists()
    assert result.evidence
