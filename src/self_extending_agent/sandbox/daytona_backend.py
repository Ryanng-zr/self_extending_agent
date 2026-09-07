from __future__ import annotations

import json
from typing import Any

from self_extending_agent.models import VerificationResult
from .base import SandboxBackend
from .static_checks import validate_generated_source
from .local import _verification_harness, _execution_harness


class DaytonaSandbox(SandboxBackend):
    """
    Stronger isolation adapter. Generated code runs in a Daytona sandbox,
    not in the main application process.

    Daytona reads credentials from its standard environment variables.
    """

    def _create(self):
        try:
            from daytona import Daytona
        except ImportError as exc:
            raise RuntimeError(
                "Install the Daytona extra first: pip install -e '.[daytona]'"
            ) from exc
        client = Daytona()
        return client, client.create()

    def verify(
        self,
        source: str,
        generated_tests: list[dict[str, Any]],
        timeout_seconds: int,
    ) -> VerificationResult:
        reasons = validate_generated_source(source)
        if reasons:
            return VerificationResult(
                passed=False, exit_code=1, reasons=reasons
            )

        client, sandbox = self._create()
        try:
            result = sandbox.process.code_run(
                _verification_harness(source, generated_tests)
            )
            stdout = result.result or ""
            passed = '"passed": true' in stdout.lower()
            return VerificationResult(
                passed=passed,
                exit_code=0 if passed else 2,
                stdout=stdout,
                reasons=[] if passed else ["Generated tool failed Daytona verification."],
            )
        finally:
            # SDK versions differ in lifecycle helpers. Best-effort cleanup.
            try:
                client.delete(sandbox)
            except Exception:
                pass

    def execute(
        self,
        source: str,
        arguments: dict[str, Any],
        timeout_seconds: int,
    ) -> Any:
        reasons = validate_generated_source(source)
        if reasons:
            raise RuntimeError("Generated source rejected: " + "; ".join(reasons))

        client, sandbox = self._create()
        try:
            result = sandbox.process.code_run(
                _execution_harness(source, arguments)
            )
            return json.loads(result.result.strip())
        finally:
            try:
                client.delete(sandbox)
            except Exception:
                pass
