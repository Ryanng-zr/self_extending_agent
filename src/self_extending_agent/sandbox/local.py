from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from self_extending_agent.models import VerificationResult
from .base import SandboxBackend
from .static_checks import validate_generated_source


def _verification_harness(
    source: str,
    tests: list[dict[str, Any]],
) -> str:
    tests_literal = repr(tests)
    return f"""
import json
import math

{source}

TESTS = {tests_literal}

def close_enough(actual, expected, tolerance):
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return abs(actual - expected) <= tolerance
    return actual == expected

failures = []
for index, test in enumerate(TESTS):
    try:
        output = run(test["input"])
        expected = test["expected"]
        tolerance = float(test.get("tolerance", 0))
        if "path" in test:
            actual = output
            for part in test["path"].split("."):
                actual = actual[part]
        else:
            actual = output

        if not close_enough(actual, expected, tolerance):
            failures.append(
                f"test {{index}} failed: actual={{actual!r}}, expected={{expected!r}}"
            )
    except Exception as exc:
        failures.append(f"test {{index}} raised {{type(exc).__name__}}: {{exc}}")

if failures:
    print(json.dumps({{"passed": False, "failures": failures}}))
    raise SystemExit(2)

print(json.dumps({{"passed": True, "tests": len(TESTS)}}))
"""


def _execution_harness(source: str, arguments: dict[str, Any]) -> str:
    payload = repr(arguments)
    return f"""
import json
import math

{source}

arguments = {payload}
result = run(arguments)
print(json.dumps(result))
"""


class LocalSubprocessSandbox(SandboxBackend):
    """
    Development fallback.

    IMPORTANT: a local subprocess is NOT a strong security boundary.
    Static checks reduce obvious risk, but production should use Daytona,
    a container/VM, seccomp, or another real isolation mechanism.
    """

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

        harness = _verification_harness(source, generated_tests)
        try:
            proc = subprocess.run(
                [sys.executable, "-I", "-c", harness],
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                env={},
            )
        except subprocess.TimeoutExpired:
            return VerificationResult(
                passed=False,
                exit_code=124,
                reasons=["Verification timed out."],
            )

        passed = proc.returncode == 0
        return VerificationResult(
            passed=passed,
            exit_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            reasons=[] if passed else ["Generated tool failed verification."],
        )

    def execute(
        self,
        source: str,
        arguments: dict[str, Any],
        timeout_seconds: int,
    ) -> Any:
        reasons = validate_generated_source(source)
        if reasons:
            raise RuntimeError("Generated source rejected: " + "; ".join(reasons))

        harness = _execution_harness(source, arguments)
        proc = subprocess.run(
            [sys.executable, "-I", "-c", harness],
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
            env={},
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr or proc.stdout)
        return json.loads(proc.stdout.strip())
