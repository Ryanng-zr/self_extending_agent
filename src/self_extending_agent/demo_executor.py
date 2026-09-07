from __future__ import annotations

import re
import uuid

from self_extending_agent.models import ToolExecutionRecord
from self_extending_agent.tools.registry import ToolRegistry


def _record(tool, inputs, output):
    return ToolExecutionRecord(
        tool=tool.name,
        tool_version=tool.version,
        generated=tool.generated,
        verified=tool.verified,
        inputs=inputs,
        output=output,
        execution_id=str(uuid.uuid4()),
    )


def execute_demo_distance(
    user_request: str,
    registry: ToolRegistry,
) -> list[ToolExecutionRecord]:
    """
    Deterministic offline execution used only for the supplied demo.

    It recognizes names that exist in data/locations.json. This keeps unit
    tests independent of any LLM provider.
    """
    list_tool = registry.get("list_locations")
    coord_tool = registry.get("get_location_coordinates")
    dist_tool = registry.get("calculate_geographic_distance")
    if not all([list_tool, coord_tool, dist_tool]):
        raise RuntimeError("Required demo tools are not registered.")

    available = list_tool.function()["locations"]
    mentioned = [
        name for name in available
        if name.lower() in user_request.lower()
    ]
    if len(mentioned) != 2:
        raise ValueError(
            "Demo mode requires exactly two known location names in the request. "
            f"Known locations: {available}"
        )

    records = []
    coords = []
    for name in mentioned:
        output = coord_tool.function(location_name=name)
        records.append(_record(coord_tool, {"location_name": name}, output))
        coords.append(output)

    args = {
        "lat1": coords[0]["latitude"],
        "lon1": coords[0]["longitude"],
        "lat2": coords[1]["latitude"],
        "lon2": coords[1]["longitude"],
    }
    output = dist_tool.function(**args)
    records.append(_record(dist_tool, args, output))
    return records
