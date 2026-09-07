from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class CapabilityRequirement(BaseModel):
    """Capabilities needed to satisfy one user request."""
    goal: str
    required_capabilities: list[str] = Field(default_factory=list)


class DiscoveryDecision(BaseModel):
    """Result of searching the complete registered tool catalogue."""
    goal: str
    selected_tools: list[str] = Field(default_factory=list)
    covered_capabilities: list[str] = Field(default_factory=list)
    missing_capabilities: list[str] = Field(default_factory=list)
    explanation: str = ""

class GeneratedToolTest(BaseModel):
    input: dict[str, Any]
    expected: Any
    path: str | None = None
    tolerance: float = 0.0


class GeneratedToolSpec(BaseModel):
    name: str = Field(
        pattern=r"^[a-z][a-z0-9_]{2,80}$"
    )
    description: str
    capabilities: list[str]

    inputs: dict[
        str,
        Literal["str", "int", "float", "bool"]
    ]

    output_description: str
    source: str

    generated_tests: list[GeneratedToolTest] = Field(
        default_factory=list
    )

# class GeneratedToolSpec(BaseModel):
#     """Machine-readable contract for one synthesized tool."""
#     name: str = Field(pattern=r"^[a-z][a-z0-9_]{2,80}$")
#     description: str
#     capabilities: list[str]
#     inputs: dict[str, Literal["str", "int", "float", "bool"]]
#     output_description: str
#     source: str
#     generated_tests: list[dict[str, Any]] = Field(default_factory=list)


class ToolManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    version: int = 1
    description: str
    capabilities: list[str]
    inputs: dict[str, Literal["str", "int", "float", "bool"]]
    output_description: str
    source_path: str
    generated: bool = True
    verified: bool = False


class VerificationResult(BaseModel):
    passed: bool
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    reasons: list[str] = Field(default_factory=list)


class ToolExecutionRecord(BaseModel):
    tool: str
    tool_version: int
    generated: bool
    verified: bool
    inputs: dict[str, Any]
    output: Any
    execution_id: str


class WorkflowResult(BaseModel):
    answer: str
    requirement: CapabilityRequirement
    discovery: DiscoveryDecision
    generated_tools: list[str] = Field(default_factory=list)
    evidence: list[ToolExecutionRecord] = Field(default_factory=list)
    trace: list[str] = Field(default_factory=list)

from typing import Any
from pydantic import BaseModel, Field


class ToolPlanStep(BaseModel):
    id: str
    tool: str
    arguments: dict[str, Any] = Field(
        default_factory=dict
    )


class ToolExecutionPlan(BaseModel):
    steps: list[ToolPlanStep]