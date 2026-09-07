from __future__ import annotations

import json
from pathlib import Path
from self_extending_agent.models import GeneratedToolSpec, ToolManifest
from self_extending_agent.dynamic_tools import (
    registered_generated_tool,
)
from self_extending_agent.models import (
    GeneratedToolSpec,
)


def load_generated_tools(
    *,
    generated_root: Path,
    registry,
    sandbox,
    timeout_seconds: int,
) -> None:
    """
    Restore previously generated and verified tools
    into the runtime registry.
    """

    if not generated_root.exists():
        return

    for tool_dir in generated_root.iterdir():

        if not tool_dir.is_dir():
            continue

        manifest_path = (
            tool_dir / "manifest.json"
        )

        source_path = (
            tool_dir / "tool.py"
        )

        tests_path = (
            tool_dir / "system_tests.json"
        )

        if (
            not manifest_path.exists()
            or not source_path.exists()
        ):
            continue

        try:
            manifest = json.loads(
                manifest_path.read_text()
            )

            source = (
                source_path.read_text()
            )

            tests = []

            if tests_path.exists():
                tests = json.loads(
                    tests_path.read_text()
                )

            tool_name = manifest["name"]

            # Never let a generated tool
            # overwrite a built-in/trusted tool.
            if tool_name in registry.names():
                continue

            spec = GeneratedToolSpec(
                name=tool_name,
                description=manifest[
                    "description"
                ],
                capabilities=manifest[
                    "capabilities"
                ],
                inputs=manifest[
                    "inputs"
                ],
                output_description=manifest.get(
                    "output_description",
                    "",
                ),
                source=source,
                generated_tests=tests,
            )

            registered_tool = (
                registered_generated_tool(
                    spec=spec,
                    sandbox=sandbox,
                    timeout_seconds=(
                        timeout_seconds
                    ),
                )
            )

            registry.register(
                registered_tool
            )

        except Exception as exc:
            raise RuntimeError(
                "Failed to restore generated "
                f"tool from {tool_dir}: {exc}"
            ) from exc

class GeneratedToolStore:
    def __init__(self, root: Path):
        self.root = root

    def persist_verified(self, spec: GeneratedToolSpec) -> ToolManifest:
        folder = self.root / spec.name
        folder.mkdir(parents=True, exist_ok=True)

        source_path = folder / "tool.py"
        source_path.write_text(spec.source)

        manifest = ToolManifest(
            name=spec.name,
            version=1,
            description=spec.description,
            capabilities=spec.capabilities,
            inputs=spec.inputs,
            output_description=spec.output_description,
            source_path=str(source_path),
            generated=True,
            verified=True,
        )
        (folder / "manifest.json").write_text(
            manifest.model_dump_json(indent=2)
        )
        # (folder / "generated_tests.json").write_text(
        #     json.dumps(spec.generated_tests, indent=2)
        # )
        (folder / "generated_tests.json").write_text(
            json.dumps(
                [
                    test.model_dump()
                    for test in spec.generated_tests
                ],
                indent=2,
            )
        )
        return manifest
