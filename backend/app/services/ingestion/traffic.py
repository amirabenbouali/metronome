"""Live traffic-congestion signal via NYC DOT's real-time traffic speed feed.

Free, no API key required. See:
https://data.cityofnewyork.us/Transportation/DOT-Traffic-Speeds-NBE/i4gi-tjb9

The dataset reports speed per monitored road segment ("link"), not per
zone, and the sensor network is sparse - test queries found zero monitored
links within 3km of some zone centroids (e.g. Williamsburg). So rather than
matching individual links to each zone's small footprint, this averages all
links reporting recently in the zone's borough - a coarser proxy, same
spirit as the community-board approach in events.py.

The feed itself isn't always fresh (observed multi-hour gaps between
updates during development), so rather than filtering to a tight recent
window and getting nothing back during a gap, this just takes each link's
latest available reading, however old, and lets the response's own
`data_as_of` values reflect actual freshness.
"""

import time

import httpx

SOCRATA_BASE = "https://data.cityofnewyork.us/resource/i4gi-tjb9.json"
USER_AGENT = "Metronome/0.1 (+https://github.com/amirabenbouali/metronome)"

# zone slug -> NYC borough, as used in the traffic dataset
ZONE_BOROUGH: dict[str, str] = {
    "midtown": "Manhattan",
    "downtown": "Manhattan",
    "upper-west-side": "Manhattan",
    "williamsburg": "Brooklyn",
    "long-island-city": "Queens",
}

_CACHE_TTL_SECONDS = 300  # traffic moves faster than weather/events; shorter TTL
_cache: dict[str, tuple[float, float]] = {}  # borough -> (congestion, fetched_at)


async def fetch_traffic_congestion(borough: str) -> float | None:
    """Return a 0-1 congestion score for a borough, or None if unavailable."""
    now = time.monotonic()

    cached = _cache.get(borough)
    if cached is not None and now - cached[1] < _CACHE_TTL_SECONDS:
        return cached[0]

    congestion = await _fetch_live_congestion(borough)
    if congestion is not None:
        _cache[borough] = (congestion, now)
    return congestion


async def _fetch_live_congestion(borough: str) -> float | None:
    params = {
        "$where": f"borough='{borough}'",
        "$order": "data_as_of DESC",
        "$select": "link_id,speed",
        "$limit": "2000",
    }
    headers = {"User-Agent": USER_AGENT}

    async with httpx.AsyncClient(timeout=5.0, headers=headers) as client:
        try:
            resp = await client.get(SOCRATA_BASE, params=params)
            resp.raise_for_status()
            rows = resp.json()
        except httpx.HTTPError:
            return None

    # Keep only the latest reading per link (rows are ordered newest-first).
    latest_speed_by_link: dict[str, float] = {}
    for row in rows:
        link_id = row.get("link_id")
        speed = row.get("speed")
        if link_id is None or speed is None or link_id in latest_speed_by_link:
            continue
        try:
            latest_speed_by_link[link_id] = float(speed)
        except ValueError:
            continue

    if not latest_speed_by_link:
        return None

    avg_speed = sum(latest_speed_by_link.values()) / len(latest_speed_by_link)
    return _congestion_from_speed(avg_speed)


def _congestion_from_speed(avg_speed_mph: float) -> float:
    # 30mph is a reasonable "flowing, uncongested" reference for NYC arterial
    # roads; calibrated against live borough averages (Manhattan ~12mph,
    # Brooklyn/Queens ~22-25mph on an ordinary weekday).
    return round(min(max(1 - avg_speed_mph / 30.0, 0.0), 1.0), 2)
