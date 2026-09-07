from __future__ import annotations

import json
from pathlib import Path
from .registry import ToolRegistry
from .types import RegisteredTool


_DATA = Path(__file__).resolve().parents[1] / "data" / "locations.json"


def get_location_coordinates(location_name: str) -> dict:
    """Retrieve latitude and longitude for a named place in the application data."""
    records = json.loads(_DATA.read_text())
    if location_name not in records:
        raise ValueError(
            f"Unknown location {location_name!r}. "
            f"Known locations: {', '.join(sorted(records))}"
        )
    return records[location_name]


def list_locations() -> dict:
    """List locations that exist in the demo application's data store."""
    records = json.loads(_DATA.read_text())
    return {"locations": sorted(records)}

def get_lat_lon(args: dict) -> dict:
    location_name = args["location_name"]

    if location_name == "Location A":
        return {
            "lat": 1.3521,
            "lon": 103.8198,
        }

    if location_name == "Location B":
        return {
            "lat": 35.6762,
            "lon": 139.6503,
        }

    if location_name == "Location C":
            return {
                "lat": 40.7128,
                "lon": 139.6503,
            }

    if location_name == "Location D":
            return {
                "lat": 51.5074,
                "lon": 139.6503,
            }

    raise ValueError(
        f"Unknown location: {location_name}"
    )


def build_builtin_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        RegisteredTool(
            name="get_lat_lon",
            description=(
                "Retrieve latitude and longitude for a named location. "
                "This is currently a dummy implementation returning fixed values."
            ),
            capabilities=[
                "retrieve location coordinates",
                "retrieve latitude and longitude",
                "look up coordinates",
            ],
            input_schema={
                "location_name": "str",
            },
            function=get_lat_lon,
            generated=False,
            verified=True,
        )
    )
    # registry.register(
    #     RegisteredTool(
    #         name="get_location_coordinates",
    #         description=(
    #             "Retrieve latitude and longitude for a named location from "
    #             "the application's trusted data store."
    #         ),
    #         capabilities=[
    #             "retrieve location coordinates",
    #             "retrieve latitude and longitude",
    #             "look up coordinates",
    #         ],
    #         aliases=["get coordinates", "retrieve coordinates"],
    #         input_schema={"location_name": "str"},
    #         function=get_location_coordinates,
    #     )
    # )
    # registry.register(
    #     RegisteredTool(
    #         name="list_locations",
    #         description="List location names available in the application's data store.",
    #         capabilities=["list locations", "discover location names"],
    #         input_schema={},
    #         function=list_locations,
    #     )
    # )
    return registry
