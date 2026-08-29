"""Live traffic-congestion signal via TfL's road corridor status feed.

Free, no API key required (a key is only needed for higher rate limits).
See: https://api.tfl.gov.uk/swagger/ui/index.html#!/Road

TfL reports status per major road corridor (A-roads, ring roads, river
crossings - ~24 total across London), each with a bounding box, rather than
per exact location. Each zone (a full borough's bounding box) is matched
against every corridor whose bounding box overlaps it at all; congestion is
the average of their severities.
"""

import asyncio
import json
import time
from typing import NamedTuple

import httpx

# (min_lat, max_lat, min_lng, max_lng)
BBox = tuple[float, float, float, float]

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
_roads_lock = asyncio.Lock()

_CONGESTION_CACHE_TTL_SECONDS = 300
_congestion_cache: dict[BBox, tuple["TrafficReading", float]] = {}


class TrafficReading(NamedTuple):
    congestion: float  # 0-1
    description: str  # plain-language summary naming the worst matched road(s)


async def fetch_traffic_congestion(bbox: BBox) -> TrafficReading | None:
    """Return a congestion reading for a zone's bounding box, or None if unavailable."""
    key = tuple(round(v, 3) for v in bbox)
    now = time.monotonic()

    cached = _congestion_cache.get(key)
    if cached is not None and now - cached[1] < _CONGESTION_CACHE_TTL_SECONDS:
        return cached[0]

    roads = await _fetch_roads()
    if roads is None:
        return None

    matched = [road for road in roads if _bboxes_overlap(bbox, road["bounds"])]
    if not matched:
        return None

    scores = [
        _SEVERITY_SCORES.get(road["statusSeverity"].lower(), _UNKNOWN_SEVERITY_SCORE)
        for road in matched
    ]
    congestion = round(sum(scores) / len(scores), 2)
    reading = TrafficReading(congestion=congestion, description=_describe(matched))
    _congestion_cache[key] = (reading, now)
    return reading


async def _fetch_roads() -> list[dict] | None:
    global _roads_cache

    if _roads_cache is not None and time.monotonic() - _roads_cache[1] < _ROADS_CACHE_TTL_SECONDS:
        return _roads_cache[0]

    async with _roads_lock:
        # Re-check: with up to 33 zones calling this concurrently, another
        # caller may have already refreshed the cache while we waited for
        # the lock - without this, every one of them would fire its own
        # request on a cold cache instead of sharing one fetch.
        if _roads_cache is not None and time.monotonic() - _roads_cache[1] < _ROADS_CACHE_TTL_SECONDS:
            return _roads_cache[0]

        headers = {"User-Agent": USER_AGENT}
        async with httpx.AsyncClient(timeout=5.0, headers=headers) as client:
            try:
                resp = await client.get(TFL_ROAD_URL)
                resp.raise_for_status()
                roads = resp.json()
            except httpx.HTTPError:
                return None

        _roads_cache = (roads, time.monotonic())
        return roads


def _bboxes_overlap(zone_bbox: BBox, road_bounds_json: str) -> bool:
    zone_min_lat, zone_max_lat, zone_min_lng, zone_max_lng = zone_bbox
    try:
        (lng1, lat1), (lng2, lat2) = json.loads(road_bounds_json)
    except (ValueError, TypeError):
        return False
    road_min_lat, road_max_lat = min(lat1, lat2), max(lat1, lat2)
    road_min_lng, road_max_lng = min(lng1, lng2), max(lng1, lng2)
    return zone_min_lat <= road_max_lat and zone_max_lat >= road_min_lat and (
        zone_min_lng <= road_max_lng and zone_max_lng >= road_min_lng
    )


def _describe(matched: list[dict]) -> str:
    worst_first = sorted(
        matched,
        key=lambda r: _SEVERITY_SCORES.get(r["statusSeverity"].lower(), _UNKNOWN_SEVERITY_SCORE),
        reverse=True,
    )
    if _SEVERITY_SCORES.get(worst_first[0]["statusSeverity"].lower(), _UNKNOWN_SEVERITY_SCORE) <= 0.1:
        return f"Roads flowing normally ({len(matched)} corridors checked)"

    names = [r["displayName"] for r in worst_first[:2]]
    status = worst_first[0]["statusSeverityDescription"]
    return f"{' and '.join(names)}: {status.lower()}"
