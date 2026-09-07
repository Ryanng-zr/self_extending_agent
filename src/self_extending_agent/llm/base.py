from __future__ import annotations

from abc import ABC, abstractmethod
from self_extending_agent.models import (
    CapabilityRequirement,
    DiscoveryDecision,
    GeneratedToolSpec,
    ToolExecutionRecord,
    ToolExecutionPlan
)


class WorkflowModel(ABC):
    @abstractmethod
    def create_execution_plan(
        self,
        user_request: str,
        available_tools: str,
    ) -> ToolExecutionPlan:
        ...
    @abstractmethod
    def analyze_requirements(
        self, user_request: str, catalogue: str
    ) -> CapabilityRequirement:
        raise NotImplementedError

    @abstractmethod
    def discover_tools(
        self, user_request: str, requirement: CapabilityRequirement, catalogue: str
    ) -> DiscoveryDecision:
        raise NotImplementedError

    @abstractmethod
    def synthesize_tool(
        self,
        user_request: str,
        missing_capability: str,
        catalogue: str,
        failure_feedback: str = "",
    ) -> GeneratedToolSpec:
        raise NotImplementedError

    @abstractmethod
    def final_answer(
        self, user_request: str, evidence: list[ToolExecutionRecord]
    ) -> str:
        raise NotImplementedError
