"""Live transit-delay signal via TfL's line status feed, across all rail modes.

Free, no API key required. See:
https://api.tfl.gov.uk/swagger/ui/index.html#!/Line

Covers Tube, DLR, Overground, Elizabeth line, and Tram - Tube alone leaves
most outer boroughs with zero coverage (e.g. Bexley, Havering, Sutton have
no Underground stations at all). Rather than a hardcoded zone-to-line table
(which doesn't scale past a handful of hand-picked zones), each zone is
matched by which lines have at least one station inside its bounding box:
this is real geography, not a lookup table, so it works for all 33 London
zones without maintaining a mapping by hand.

Station-to-line topology (which stations each line serves) is essentially
static, so it's fetched once and cached for a day - only line *status*
(delays right now) needs to be fetched frequently.

Both caches are guarded by a lock with a double-checked read: with 33 zones
calling fetch_transit_delay() concurrently, an unguarded cache-miss check
would let every one of them kick off its own fetch simultaneously - for
topology specifically, each of those fans out into 20 more concurrent
requests (one per line's stop list), so an unguarded cold start meant up to
~660 concurrent requests to TfL, which got rejected en masse and made every
zone silently fall back to the mock value. Caught this by noticing all 33
zones in a real /zones response showed the *exact* same transit_delay.
"""

import asyncio
import time
from typing import NamedTuple

import httpx

# (min_lat, max_lat, min_lng, max_lng)
BBox = tuple[float, float, float, float]

TFL_MODES = "tube,dlr,overground,elizabeth-line,tram"
TFL_LINE_STATUS_URL = f"https://api.tfl.gov.uk/Line/Mode/{TFL_MODES}/Status"
USER_AGENT = "Metronome/0.1 (+https://github.com/amirabenbouali/metronome)"
MAX_CONCURRENT_STOP_REQUESTS = 5
GOOD_SERVICE_SEVERITY = 10


class LineStatus(NamedTuple):
    name: str  # e.g. "Northern"
    severity: int  # TfL's statusSeverity; 10 = Good Service, lower is worse
    description: str  # e.g. "Minor Delays"


class TransitReading(NamedTuple):
    delay: float  # 0-1
    description: str  # plain-language summary naming the worst matched line(s)


_TOPOLOGY_CACHE_TTL_SECONDS = 86_400  # station geography doesn't change day to day
_topology_cache: tuple[dict[str, list[tuple[float, float]]], float] | None = None
_topology_lock = asyncio.Lock()

_STATUS_CACHE_TTL_SECONDS = 120  # service status can change quickly
_status_cache: tuple[dict[str, LineStatus], float] | None = None
_status_lock = asyncio.Lock()

_READING_CACHE_TTL_SECONDS = 120
_reading_cache: dict[BBox, tuple[TransitReading, float]] = {}


async def fetch_transit_delay(bbox: BBox) -> TransitReading | None:
    """Return a transit delay reading for a zone's bounding box, or None if unavailable."""
    key = tuple(round(v, 3) for v in bbox)
    now = time.monotonic()

    cached = _reading_cache.get(key)
    if cached is not None and now - cached[1] < _READING_CACHE_TTL_SECONDS:
        return cached[0]

    topology, statuses = await asyncio.gather(_fetch_topology(), _fetch_line_statuses())
    if topology is None or statuses is None:
        return None

    matched_ids = [
        line_id
        for line_id, stations in topology.items()
        if any(_point_in_bbox(bbox, lat, lon) for lat, lon in stations)
    ]
    matched = [statuses[line_id] for line_id in matched_ids if line_id in statuses]
    if not matched:
        return None

    avg_severity = sum(s.severity for s in matched) / len(matched)
    # 10 = Good Service -> 0 delay; each point below scales delay up.
    delay = round(min(max((GOOD_SERVICE_SEVERITY - avg_severity) / GOOD_SERVICE_SEVERITY, 0.0), 1.0), 2)
    reading = TransitReading(delay=delay, description=_describe(matched))
    _reading_cache[key] = (reading, now)
    return reading


async def _fetch_topology() -> dict[str, list[tuple[float, float]]] | None:
    global _topology_cache

    if _topology_cache is not None and time.monotonic() - _topology_cache[1] < _TOPOLOGY_CACHE_TTL_SECONDS:
        return _topology_cache[0]

    async with _topology_lock:
        # Re-check: another caller may have already refreshed it while we
        # were waiting for the lock.
        if (
            _topology_cache is not None
            and time.monotonic() - _topology_cache[1] < _TOPOLOGY_CACHE_TTL_SECONDS
        ):
            return _topology_cache[0]

        headers = {"User-Agent": USER_AGENT}
        stop_semaphore = asyncio.Semaphore(MAX_CONCURRENT_STOP_REQUESTS)
        async with httpx.AsyncClient(timeout=5.0, headers=headers) as client:
            try:
                resp = await client.get(TFL_LINE_STATUS_URL)
                resp.raise_for_status()
                line_ids = [line["id"] for line in resp.json()]

                stops_by_line = await asyncio.gather(
                    *(_fetch_line_stops(client, line_id, stop_semaphore) for line_id in line_ids)
                )
            except httpx.HTTPError:
                return None

        topology = dict(zip(line_ids, stops_by_line))
        _topology_cache = (topology, time.monotonic())
        return topology


async def _fetch_line_stops(
    client: httpx.AsyncClient, line_id: str, semaphore: asyncio.Semaphore
) -> list[tuple[float, float]]:
    async with semaphore:
        try:
            resp = await client.get(f"https://api.tfl.gov.uk/Line/{line_id}/StopPoints")
            resp.raise_for_status()
            stops = resp.json()
        except httpx.HTTPError:
            return []
    return [(stop["lat"], stop["lon"]) for stop in stops if "lat" in stop and "lon" in stop]


async def _fetch_line_statuses() -> dict[str, LineStatus] | None:
    global _status_cache

    if _status_cache is not None and time.monotonic() - _status_cache[1] < _STATUS_CACHE_TTL_SECONDS:
        return _status_cache[0]

    async with _status_lock:
        if _status_cache is not None and time.monotonic() - _status_cache[1] < _STATUS_CACHE_TTL_SECONDS:
            return _status_cache[0]

        headers = {"User-Agent": USER_AGENT}
        async with httpx.AsyncClient(timeout=5.0, headers=headers) as client:
            try:
                resp = await client.get(TFL_LINE_STATUS_URL)
                resp.raise_for_status()
                lines = resp.json()
            except httpx.HTTPError:
                return None

        statuses: dict[str, LineStatus] = {}
        for line in lines:
            line_statuses = line.get("lineStatuses") or []
            if not line_statuses:
                continue
            # A line can carry multiple simultaneous statuses; use the worst one.
            worst = min(line_statuses, key=lambda s: s["statusSeverity"])
            statuses[line["id"]] = LineStatus(
                name=line["name"],
                severity=worst["statusSeverity"],
                description=worst["statusSeverityDescription"],
            )

        _status_cache = (statuses, time.monotonic())
        return statuses


def _point_in_bbox(bbox: BBox, lat: float, lon: float) -> bool:
    min_lat, max_lat, min_lng, max_lng = bbox
    return min_lat <= lat <= max_lat and min_lng <= lon <= max_lng


def _describe(matched: list[LineStatus]) -> str:
    worst_first = sorted(matched, key=lambda s: s.severity)
    if worst_first[0].severity >= GOOD_SERVICE_SEVERITY:
        return f"All lines running normally ({len(matched)} checked)"

    worst_severity = worst_first[0].severity
    worst_names = [s.name for s in worst_first if s.severity == worst_severity][:2]
    return f"{' and '.join(worst_names)} line{'s' if len(worst_names) > 1 else ''}: {worst_first[0].description.lower()}"
