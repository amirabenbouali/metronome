"""Live traffic-congestion signal via TfL's road corridor status feed.

Free, no API key required (a key is only needed for higher rate limits).
See: https://api.tfl.gov.uk/swagger/ui/index.html#!/Road

TfL reports status per major road corridor (A-roads, ring roads, river
crossings - ~24 total across London), each with a bounding box, rather than
per exact location. Each zone is matched against every corridor whose
bounding box contains its centroid; congestion is the average of their
severities. Coverage is decent this way (every zone matched at least 2
corridors when checked against Camden/Shoreditch/South Bank/Canary
Wharf/Paddington), unlike the original NYC version where some zones had zero
nearby monitored links.
"""

import json
import time

import httpx

TFL_ROAD_URL = "https://api.tfl.gov.uk/Road"
USER_AGENT = "Metronome/0.1 (+https://github.com/amirabenbouali/metronome)"

# TfL's disruption severity vocabulary, worst to best. Unrecognized values
# fall back to a mid-range guess rather than being dropped.
_SEVERITY_SCORES: dict[str, float] = {
    "severe": 0.9,
    "serious": 0.7,
    "moderate": 0.5,
    "minor": 0.3,
    "good": 0.1,
}
_UNKNOWN_SEVERITY_SCORE = 0.4

_ROADS_CACHE_TTL_SECONDS = 300
_roads_cache: tuple[list[dict], float] | None = None

_CONGESTION_CACHE_TTL_SECONDS = 300
_congestion_cache: dict[tuple[float, float], tuple[float, float]] = {}


async def fetch_traffic_congestion(lat: float, lng: float) -> float | None:
    """Return a 0-1 congestion score for a point, or None if unavailable."""
    key = (round(lat, 3), round(lng, 3))
    now = time.monotonic()

    cached = _congestion_cache.get(key)
    if cached is not None and now - cached[1] < _CONGESTION_CACHE_TTL_SECONDS:
        return cached[0]

    roads = await _fetch_roads()
    if roads is None:
        return None

    matched_scores = [
        _SEVERITY_SCORES.get(road["statusSeverity"].lower(), _UNKNOWN_SEVERITY_SCORE)
        for road in roads
        if _point_in_bounds(lat, lng, road["bounds"])
    ]
    if not matched_scores:
        return None

    congestion = round(sum(matched_scores) / len(matched_scores), 2)
    _congestion_cache[key] = (congestion, now)
    return congestion


async def _fetch_roads() -> list[dict] | None:
    global _roads_cache
    now = time.monotonic()

    if _roads_cache is not None and now - _roads_cache[1] < _ROADS_CACHE_TTL_SECONDS:
        return _roads_cache[0]

    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient(timeout=5.0, headers=headers) as client:
        try:
            resp = await client.get(TFL_ROAD_URL)
            resp.raise_for_status()
            roads = resp.json()
        except httpx.HTTPError:
            return None

    _roads_cache = (roads, now)
    return roads


def _point_in_bounds(lat: float, lng: float, bounds_json: str) -> bool:
    try:
        (lng1, lat1), (lng2, lat2) = json.loads(bounds_json)
    except (ValueError, TypeError):
        return False
    return min(lat1, lat2) <= lat <= max(lat1, lat2) and min(lng1, lng2) <= lng <= max(lng1, lng2)
