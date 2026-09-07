from __future__ import annotations

import json
from typing import TypeVar, Type

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from self_extending_agent.models import (
    CapabilityRequirement,
    DiscoveryDecision,
    GeneratedToolSpec,
    ToolExecutionRecord,
    ToolExecutionPlan,
)
from .base import WorkflowModel

T = TypeVar("T")


class LangChainWorkflowModel(WorkflowModel):
    def __init__(self, model: str):
        self.model_name = model
        self.model = init_chat_model(
            model=model,
            temperature=0,
        )

    def create_execution_plan(
        self,
        user_request: str,
        available_tools: str,
    ) -> ToolExecutionPlan:

        planner = self.model.with_structured_output(
            ToolExecutionPlan
        )

        prompt = f"""
    You are an execution planner.

    Your job is to create a sequence of tool calls that
    satisfies the user's request.

    USER REQUEST:
    {user_request}

    AVAILABLE TOOLS:
    {available_tools}

    Rules:

    1. Use ONLY tools listed in AVAILABLE TOOLS.
    2. Do NOT invent tool names.
    3. Do NOT perform calculations yourself.
    4. Use previous tool outputs as inputs when needed.
    5. A reference to a previous output must use:

    $<step_id>.<field>

    Example:

    $coords_a.latitude

    6. Each step ID must be unique.
    7. Arrange steps in dependency order.
    8. Do not synthesize tools here.
    9. Do not answer the user here.
    """

        return planner.invoke(prompt)

    def _structured(self, schema: Type[T], system_prompt: str, user_text: str) -> T:
        agent = create_agent(
            model=self.model,
            tools=[],
            response_format=schema,
            system_prompt=system_prompt,
        )
        result = agent.invoke(
            {"messages": [{"role": "user", "content": user_text}]}
        )
        return result["structured_response"]

    def analyze_requirements(
        self, user_request: str, catalogue: str
    ) -> CapabilityRequirement:
        return self._structured(
            CapabilityRequirement,
            """
You are the requirement-analysis stage of a controlled agent system.

Identify the capabilities that are actually necessary to satisfy the user's
request. Use concise, implementation-neutral capability phrases.

You are given the COMPLETE current tool catalogue for context.
Do not answer the request.
Do not write code.
Do not claim a tool exists unless it appears in the catalogue.
""",
            f"USER REQUEST:\n{user_request}\n\nFULL TOOL CATALOGUE:\n{catalogue}",
        )

    def discover_tools(
        self,
        user_request: str,
        requirement: CapabilityRequirement,
        catalogue: str,
    ) -> DiscoveryDecision:
        return self._structured(
            DiscoveryDecision,
            """
You are the mandatory tool-discovery gate.

You MUST inspect the ENTIRE provided tool catalogue before declaring any
capability missing. Prefer composition of existing tools over synthesizing a
new tool. A capability is missing only when no registered tool or combination
of registered tools can provide it.

selected_tools MUST contain only exact tool names from the catalogue.
covered_capabilities should state which required capabilities those tools cover.
missing_capabilities should contain only capabilities that truly cannot be
satisfied by the catalogue.

Do not answer the user's question and do not write code.
""",
            (
                f"USER REQUEST:\n{user_request}\n\n"
                f"REQUIREMENT:\n{requirement.model_dump_json(indent=2)}\n\n"
                f"FULL TOOL CATALOGUE:\n{catalogue}"
            ),
        )

    def synthesize_tool(
        self,
        user_request: str,
        missing_capability: str,
        catalogue: str,
        failure_feedback: str = "",
    ) -> GeneratedToolSpec:
        return self._structured(
            GeneratedToolSpec,
            """
You are the tool-synthesis stage. You are called ONLY after mandatory
discovery has proved that a capability is missing.

Create one small, deterministic, pure-Python tool for the missing capability.

STRICT CONTRACT:
1. Source MUST define exactly one public entry point:
       def run(args: dict) -> dict
2. Do not use files, network, subprocesses, environment variables, eval, exec,
   dynamic imports, user input, or external packages.
3. Standard-library mathematical operations are allowed. `math` is already
   available in the execution harness, so do not import it.
4. Never fabricate external facts. The tool should transform/compute only from
   its explicit inputs.
5. Keep source minimal.
6. Provide tests with explicit inputs and expected outputs.
7. If the capability cannot be safely implemented as a deterministic pure
   function, do not pretend otherwise; emit a tool whose run() raises a clear
   ValueError explaining that external trusted data/integration is required.

Do not recreate any tool already present in the catalogue.

TEST FORMAT IS STRICT.

Every generated_tests item MUST contain exactly:

{
  "input": {
    "<argument>": <value>
  },
  "expected": <expected value>,
  "path": "<optional dotted key inside returned dict>",
  "tolerance": <numeric tolerance>
}

Example:

{
  "input": {
    "lat1": 0,
    "lon1": 0,
    "lat2": 0,
    "lon2": 1
  },
  "expected": 111.195,
  "path": "distance_km",
  "tolerance": 0.2
}

Do NOT use keys such as:
- inputs
- expected_output
- output
- result
- args
""",
            (
                f"USER REQUEST:\n{user_request}\n\n"
                f"MISSING CAPABILITY:\n{missing_capability}\n\n"
                f"FULL EXISTING TOOL CATALOGUE:\n{catalogue}\n\n"
                f"PREVIOUS FAILURE FEEDBACK:\n{failure_feedback or '(none)'}"
            ),
        )

    def final_answer(
        self,
        user_request: str,
        evidence: list[ToolExecutionRecord],
    ) -> str:
        evidence_json = json.dumps(
            [e.model_dump() for e in evidence],
            indent=2,
            default=str,
        )
        agent = create_agent(
            model=self.model,
            tools=[],
            system_prompt="""
Answer the user using ONLY the VERIFIED TOOL EVIDENCE provided.

Rules:
- Do not independently calculate factual values.
- Do not invent missing tool outputs.
- If evidence is insufficient, explicitly say that the requested result could
  not be verified.
- Briefly distinguish source data from computed/generated-tool output when useful.
""",
        )
        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"ORIGINAL REQUEST:\n{user_request}\n\n"
                            f"VERIFIED TOOL EVIDENCE:\n{evidence_json}"
                        ),
                    }
                ]
            }
        )
        message = result["messages"][-1]

        text_parts = [
            block["text"]
            for block in message.content_blocks
            if block.get("type") == "text"
        ]

        return "\n".join(text_parts)
