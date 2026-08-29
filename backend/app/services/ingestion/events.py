"""Live event-density signal via the Ticketmaster Discovery API.

Unlike the other adapters, this needs a free API key - no zero-signup,
city-wide London events feed was found (checked TfL's full API surface,
London Datastore's ~1300 datasets, Royal Parks, and Eventbrite's public
search, which now requires OAuth). Ticketmaster's Discovery API covers large
ticketed events (concerts, sports, theatre) - a different flavor of
"activity" than the original NYC version's permitted-events feed (which
covered any street-level permit, including routine park maintenance), but
still a legitimate live pulse signal.

Set TICKETMASTER_API_KEY in backend/.env to enable; event_density falls
back to the mock value if unset or a request fails.

With 33 zones (every London borough) each firing their own geo-radius
query, a free-tier key's burst rate limit becomes a real risk - a spot
check during development saw an occasional failure at just 5 concurrent
requests. A semaphore caps how many run at once; the cache TTL is longer
than the other adapters' since events don't change minute to minute.
"""

import asyncio
import math
import time
from datetime import datetime, timezone
from typing import NamedTuple

import httpx

from app.core.config import settings

DISCOVERY_EVENTS_URL = "https://app.ticketmaster.com/discovery/v2/events.json"
# Boroughs vary hugely in size (City of London vs. Bromley), and the API
# only takes a single point + radius, not a polygon - this is a compromise
# radius rather than a precise per-zone fit.
SEARCH_RADIUS_KM = 3
MAX_CONCURRENT_REQUESTS = 5

# Calibrated against live counts (checked 2026-08-28: 3-109 events found
# today within 2km across 5 central zones - South Bank's West End-adjacent
# venue density dwarfing everywhere else). A log scale keeps that spread
# meaningful instead of either saturating everything or flattening the low
# end, which a linear cap would do given the ~35x range between zones.
_DENSITY_LOG_CAP = 150

_CACHE_TTL_SECONDS = 1200
_cache: dict[tuple[float, float], tuple["EventReading", float]] = {}
_request_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)


class EventReading(NamedTuple):
    density: float  # 0-1
    description: str  # plain-language summary, naming an event when there is one


async def fetch_event_density(lat: float, lng: float) -> EventReading | None:
    """Return an event reading for a point, or None if unavailable/unconfigured."""
    if not settings.ticketmaster_api_key:
        return None

    key = (round(lat, 3), round(lng, 3))
    now = time.monotonic()

    cached = _cache.get(key)
    if cached is not None and now - cached[1] < _CACHE_TTL_SECONDS:
        return cached[0]

    reading = await _fetch_live_reading(lat, lng)
    if reading is not None:
        _cache[key] = (reading, now)
    return reading


async def _fetch_live_reading(lat: float, lng: float) -> EventReading | None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    params = {
        "latlong": f"{lat},{lng}",
        "radius": str(SEARCH_RADIUS_KM),
        "unit": "km",
        "startDateTime": f"{today}T00:00:00Z",
        "endDateTime": f"{today}T23:59:59Z",
        "size": "3",  # a few real event names for the description, not just the count
        "apikey": settings.ticketmaster_api_key,
    }

    async with _request_semaphore, httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(DISCOVERY_EVENTS_URL, params=params)
            resp.raise_for_status()
            body = resp.json()
            total = body.get("page", {}).get("totalElements", 0)
            events = body.get("_embedded", {}).get("events", [])
        except (httpx.HTTPError, ValueError, KeyError):
            return None

    density = _density_from_count(total)
    description = _describe(total, events)
    return EventReading(density=density, description=description)


def _density_from_count(count: int) -> float:
    density = math.log10(count + 1) / math.log10(_DENSITY_LOG_CAP + 1)
    return round(min(max(density, 0.0), 1.0), 2)


def _describe(total: int, sample_events: list[dict]) -> str:
    if total == 0:
        return f"No major events today within {SEARCH_RADIUS_KM}km"
    if total == 1 and sample_events:
        return f"1 event today: {sample_events[0].get('name', 'an event nearby')}"
    example = sample_events[0].get("name") if sample_events else None
    if example:
        return f"{total} events today, including {example}"
    return f"{total} events happening today nearby"
