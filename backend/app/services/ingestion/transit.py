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

import httpx

# (min_lat, max_lat, min_lng, max_lng)
BBox = tuple[float, float, float, float]

TFL_MODES = "tube,dlr,overground,elizabeth-line,tram"
TFL_LINE_STATUS_URL = f"https://api.tfl.gov.uk/Line/Mode/{TFL_MODES}/Status"
USER_AGENT = "Metronome/0.1 (+https://github.com/amirabenbouali/metronome)"
MAX_CONCURRENT_STOP_REQUESTS = 5

_TOPOLOGY_CACHE_TTL_SECONDS = 86_400  # station geography doesn't change day to day
_topology_cache: tuple[dict[str, list[tuple[float, float]]], float] | None = None
_topology_lock = asyncio.Lock()

_SEVERITY_CACHE_TTL_SECONDS = 120  # service status can change quickly
_severity_cache: tuple[dict[str, float], float] | None = None
_severity_lock = asyncio.Lock()

_DELAY_CACHE_TTL_SECONDS = 120
_delay_cache: dict[BBox, tuple[float, float]] = {}


async def fetch_transit_delay(bbox: BBox) -> float | None:
    """Return a 0-1 transit delay score for a zone's bounding box, or None if unavailable."""
    key = tuple(round(v, 3) for v in bbox)
    now = time.monotonic()

    cached = _delay_cache.get(key)
    if cached is not None and now - cached[1] < _DELAY_CACHE_TTL_SECONDS:
        return cached[0]

    topology, severities = await asyncio.gather(_fetch_topology(), _fetch_line_severities())
    if topology is None or severities is None:
        return None

    matched_lines = [
        line_id
        for line_id, stations in topology.items()
        if any(_point_in_bbox(bbox, lat, lon) for lat, lon in stations)
    ]
    matched_severities = [severities[line_id] for line_id in matched_lines if line_id in severities]
    if not matched_severities:
        return None

    avg_status_severity = sum(matched_severities) / len(matched_severities)
    # 10 = Good Service -> 0 delay; each point below scales delay up.
    delay = round(min(max((10 - avg_status_severity) / 10, 0.0), 1.0), 2)
    _delay_cache[key] = (delay, now)
    return delay


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


async def _fetch_line_severities() -> dict[str, float] | None:
    global _severity_cache

    if _severity_cache is not None and time.monotonic() - _severity_cache[1] < _SEVERITY_CACHE_TTL_SECONDS:
        return _severity_cache[0]

    async with _severity_lock:
        if (
            _severity_cache is not None
            and time.monotonic() - _severity_cache[1] < _SEVERITY_CACHE_TTL_SECONDS
        ):
            return _severity_cache[0]

        headers = {"User-Agent": USER_AGENT}
        async with httpx.AsyncClient(timeout=5.0, headers=headers) as client:
            try:
                resp = await client.get(TFL_LINE_STATUS_URL)
                resp.raise_for_status()
                lines = resp.json()
            except httpx.HTTPError:
                return None

        severities: dict[str, float] = {}
        for line in lines:
            statuses = line.get("lineStatuses") or []
            if not statuses:
                continue
            # A line can carry multiple simultaneous statuses; use the worst one.
            severities[line["id"]] = min(s["statusSeverity"] for s in statuses)

        _severity_cache = (severities, time.monotonic())
        return severities


def _point_in_bbox(bbox: BBox, lat: float, lon: float) -> bool:
    min_lat, max_lat, min_lng, max_lng = bbox
    return min_lat <= lat <= max_lat and min_lng <= lon <= max_lng
