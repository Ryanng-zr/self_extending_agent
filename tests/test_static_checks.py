from self_extending_agent.sandbox.static_checks import validate_generated_source


def test_rejects_network_import():
    source = """
import requests
def run(args: dict) -> dict:
    return {}
"""
    reasons = validate_generated_source(source)
    assert any("Forbidden import" in item for item in reasons)


def test_requires_run_entry_point():
    reasons = validate_generated_source("def hello(): return 1")
    assert any("must define run" in item for item in reasons)
