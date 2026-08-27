"""Placeholder zone geometries + signals until real ingestion is wired up.

Each zone is a small rectangle around a well-known Manhattan-area point so the
frontend has something plausible to render on the map.
"""

from app.schemas.zone import ZoneSignals


def _square(center_lng: float, center_lat: float, half_size: float = 0.006) -> list[list[list[float]]]:
    return [
        [
            [center_lng - half_size, center_lat - half_size],
            [center_lng + half_size, center_lat - half_size],
            [center_lng + half_size, center_lat + half_size],
            [center_lng - half_size, center_lat + half_size],
            [center_lng - half_size, center_lat - half_size],
        ]
    ]


MOCK_ZONES = [
    {
        "id": "midtown",
        "name": "Midtown",
        "center": (-73.9840, 40.7549),
        "signals": ZoneSignals(
            traffic_congestion=0.82, transit_delay=0.55, weather_severity=0.1, event_density=0.7
        ),
    },
    {
        "id": "downtown",
        "name": "Downtown / Financial District",
        "center": (-74.0113, 40.7075),
        "signals": ZoneSignals(
            traffic_congestion=0.45, transit_delay=0.3, weather_severity=0.1, event_density=0.2
        ),
    },
    {
        "id": "upper-west-side",
        "name": "Upper West Side",
        "center": (-73.9773, 40.7870),
        "signals": ZoneSignals(
            traffic_congestion=0.3, transit_delay=0.2, weather_severity=0.1, event_density=0.15
        ),
    },
    {
        "id": "williamsburg",
        "name": "Williamsburg",
        "center": (-73.9571, 40.7143),
        "signals": ZoneSignals(
            traffic_congestion=0.4, transit_delay=0.45, weather_severity=0.1, event_density=0.6
        ),
    },
    {
        "id": "long-island-city",
        "name": "Long Island City",
        "center": (-73.9482, 40.7447),
        "signals": ZoneSignals(
            traffic_congestion=0.25, transit_delay=0.35, weather_severity=0.1, event_density=0.1
        ),
    },
]


def mock_zone_geometry(center_lng: float, center_lat: float) -> dict:
    return {"type": "Polygon", "coordinates": _square(center_lng, center_lat)}
