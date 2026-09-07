from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from self_extending_agent.models import VerificationResult


class SandboxBackend(ABC):
    @abstractmethod
    def verify(
        self,
        source: str,
        generated_tests: list[dict[str, Any]],
        timeout_seconds: int,
    ) -> VerificationResult:
        raise NotImplementedError

    @abstractmethod
    def execute(
        self,
        source: str,
        arguments: dict[str, Any],
        timeout_seconds: int,
    ) -> Any:
        raise NotImplementedError
