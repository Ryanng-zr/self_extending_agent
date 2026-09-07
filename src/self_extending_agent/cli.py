# from __future__ import annotations

# import argparse
# import json
# from pathlib import Path

# from self_extending_agent.config import settings
# from self_extending_agent.llm.factory import build_model
# from self_extending_agent.sandbox.factory import build_sandbox
# from self_extending_agent.tools.builtin import build_builtin_registry
# from self_extending_agent.workflow import run_workflow


# def main():
#     parser = argparse.ArgumentParser(
#         description="Controlled self-extending agent demo"
#     )
#     parser.add_argument(
#         "request",
#         nargs="?",
#         default="How far is Location A from Location B?",
#     )
#     parser.add_argument(
#         "--mode",
#         choices=["demo", "llm"],
#         default="demo",
#         help="demo is deterministic/offline; llm uses the configured model",
#     )
#     parser.add_argument(
#         "--sandbox",
#         choices=["local", "daytona"],
#         default=settings.sandbox_backend,
#     )
#     parser.add_argument("--show-trace", action="store_true")
#     args = parser.parse_args()

#     registry = build_builtin_registry()
#     model_adapter = build_model(args.mode, settings.model)
#     sandbox = build_sandbox(args.sandbox)

#     generated_root = Path.cwd() / "generated_tools"

#     result = run_workflow(
#         user_request=args.request,
#         registry=registry,
#         model_adapter=model_adapter,
#         sandbox=sandbox,
#         mode=args.mode,
#         langchain_model_name=settings.model,
#         generated_root=generated_root,
#     )

#     print("\nANSWER")
#     print("------")
#     print(result.answer)

#     if result.generated_tools:
#         print("\nGENERATED TOOLS")
#         print("---------------")
#         for name in result.generated_tools:
#             print(f"- {name}")

#     print("\nEVIDENCE")
#     print("--------")
#     for record in result.evidence:
#         print(
#             json.dumps(
#                 record.model_dump(),
#                 indent=2,
#                 default=str,
#             )
#         )

#     if args.show_trace:
#         print("\nWORKFLOW TRACE")
#         print("--------------")
#         for index, line in enumerate(result.trace, 1):
#             print(f"{index:02d}. {line}")


# if __name__ == "__main__":
#     main()
from __future__ import annotations

import argparse
import json
from pathlib import Path

from self_extending_agent.config import settings
from self_extending_agent.llm.factory import build_model
from self_extending_agent.sandbox.factory import (
    build_sandbox,
)
from self_extending_agent.tools.builtin import (
    build_builtin_registry,
)
from self_extending_agent.generated_store import (
    load_generated_tools,
)
from self_extending_agent.workflow import run_workflow


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Controlled self-extending agent demo"
        )
    )

    parser.add_argument(
        "request",
        nargs="?",
        default=(
            "How far is Location A "
            "from Location B?"
        ),
    )

    parser.add_argument(
        "--mode",
        choices=["demo", "llm"],
        default="demo",
        help=(
            "demo is deterministic/offline; "
            "llm uses the configured model"
        ),
    )

    parser.add_argument(
        "--sandbox",
        choices=["local", "daytona"],
        default=settings.sandbox_backend,
    )

    parser.add_argument(
        "--show-trace",
        action="store_true",
    )

    args = parser.parse_args()

    # ---------------------------------
    # 1. Build shared infrastructure
    # ---------------------------------

    model_adapter = build_model(
        args.mode,
        settings.model,
    )

    sandbox = build_sandbox(
        args.sandbox,
    )

    generated_root = (
        Path.cwd()
        / "generated_tools"
    )

    # ---------------------------------
    # 2. Build trusted builtin registry
    # ---------------------------------

    registry = build_builtin_registry()

    # ---------------------------------
    # 3. Reload previously generated
    #    and verified tools
    # ---------------------------------

    load_generated_tools(
        generated_root=generated_root,
        registry=registry,
        sandbox=sandbox,
        timeout_seconds=(
            settings.tool_execution_timeout_seconds
        ),
    )

    # Useful while testing reuse
    if args.show_trace:
        print(
            "TOOLS AVAILABLE AT STARTUP:",
            sorted(registry.names()),
        )

    # ---------------------------------
    # 4. Run workflow
    # ---------------------------------

    result = run_workflow(
        user_request=args.request,
        registry=registry,
        model_adapter=model_adapter,
        sandbox=sandbox,
        mode=args.mode,
        langchain_model_name=settings.model,
        generated_root=generated_root,
    )

    print("\nANSWER")
    print("------")
    print(result.answer)

    if result.generated_tools:
        print("\nGENERATED TOOLS")
        print("---------------")

        for name in result.generated_tools:
            print(f"- {name}")

    print("\nEVIDENCE")
    print("--------")

    for record in result.evidence:
        print(
            json.dumps(
                record.model_dump(),
                indent=2,
                default=str,
            )
        )

    if args.show_trace:
        print("\nWORKFLOW TRACE")
        print("--------------")

        for index, line in enumerate(
            result.trace,
            1,
        ):
            print(
                f"{index:02d}. {line}"
            )


if __name__ == "__main__":
    main()