from __future__ import annotations

from self_extending_agent.models import (
    CapabilityRequirement,
    DiscoveryDecision,
    GeneratedToolSpec,
    ToolExecutionRecord,
    ToolPlanStep,
    ToolExecutionPlan
)
from .base import WorkflowModel


_DISTANCE_SOURCE = r"""
def run(args: dict) -> dict:
    lat1 = float(args["lat1"])
    lon1 = float(args["lon1"])
    lat2 = float(args["lat2"])
    lon2 = float(args["lon2"])

    radius_km = 6371.0088
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2)
        * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return {"distance_km": radius_km * c}
""".strip()


class DemoWorkflowModel(WorkflowModel):
    """
    Deterministic model used by tests and demonstrations without API keys.

    It deliberately supports only the supplied distance scenario. Unknown
    requests fail instead of fabricating a capability or result.
    """

    def create_execution_plan(
        self,
        user_request: str,
        available_tools: str,
    ) -> ToolExecutionPlan:

        return ToolExecutionPlan(
            steps=[
                ToolPlanStep(
                    id="coords_a",
                    tool="get_location_coordinates",
                    arguments={
                        "location_name": "Location A"
                    },
                ),
                ToolPlanStep(
                    id="coords_b",
                    tool="get_location_coordinates",
                    arguments={
                        "location_name": "Location B"
                    },
                ),
                ToolPlanStep(
                    id="distance",
                    tool="calculate_geographic_distance",
                    arguments={
                        "lat1": "$coords_a.latitude",
                        "lon1": "$coords_a.longitude",
                        "lat2": "$coords_b.latitude",
                        "lon2": "$coords_b.longitude",
                    },
                ),
            ]
        )

    def analyze_requirements(self, user_request: str, catalogue: str) -> CapabilityRequirement:
        text = user_request.lower()
        if "distance" in text or "how far" in text:
            return CapabilityRequirement(
                goal="calculate distance between two stored locations",
                required_capabilities=[
                    "retrieve location coordinates",
                    "calculate geographic distance",
                ],
            )
        return CapabilityRequirement(
            goal=user_request,
            required_capabilities=[],
        )

    def discover_tools(
        self,
        user_request: str,
        requirement: CapabilityRequirement,
        catalogue: str,
    ) -> DiscoveryDecision:
        selected, covered, missing = [], [], []
        if "retrieve location coordinates" in catalogue.lower():
            selected.append("get_location_coordinates")
            covered.append("retrieve location coordinates")
        if "calculate geographic distance" in catalogue.lower():
            selected.append("calculate_geographic_distance")
            covered.append("calculate geographic distance")
        else:
            if "calculate geographic distance" in requirement.required_capabilities:
                missing.append("calculate geographic distance")

        return DiscoveryDecision(
            goal=requirement.goal,
            selected_tools=selected,
            covered_capabilities=covered,
            missing_capabilities=missing,
            explanation="Deterministic demo discovery across the full catalogue.",
        )

    def synthesize_tool(
        self,
        user_request: str,
        missing_capability: str,
        catalogue: str,
        failure_feedback: str = "",
    ) -> GeneratedToolSpec:
        if missing_capability != "calculate geographic distance":
            raise RuntimeError(
                f"Demo model cannot synthesize {missing_capability!r}; "
                "use real LLM mode."
            )

        return GeneratedToolSpec(
            name="calculate_geographic_distance",
            description=(
                "Calculate great-circle distance in kilometres between two "
                "latitude/longitude coordinates using the Haversine formula."
            ),
            capabilities=["calculate geographic distance"],
            inputs={
                "lat1": "float",
                "lon1": "float",
                "lat2": "float",
                "lon2": "float",
            },
            output_description='{"distance_km": float}',
            source=_DISTANCE_SOURCE,
            generated_tests=[
                {
                    "input": {"lat1": 0, "lon1": 0, "lat2": 0, "lon2": 0},
                    "path": "distance_km",
                    "expected": 0.0,
                    "tolerance": 1e-9,
                },
                {
                    "input": {"lat1": 0, "lon1": 0, "lat2": 0, "lon2": 1},
                    "path": "distance_km",
                    "expected": 111.195,
                    "tolerance": 0.2,
                },
            ],
        )

    def final_answer(
        self, user_request: str, evidence: list[ToolExecutionRecord]
    ) -> str:
        for record in reversed(evidence):
            if record.tool == "calculate_geographic_distance":
                return (
                    f"The verified tool result is approximately "
                    f"{record.output['distance_km']:.2f} km."
                )
        return "I could not produce a verified result."
