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
# How many individual events to list per zone in the main /zones payload
# (the density score itself is based on the true total, not this sample
# size). Kept small since this fans out to all 33 zones every poll.
SAMPLE_SIZE = 8
# Ticketmaster's actual page-size ceiling, used only for the on-demand
# "see all" fetch for one specific zone - confirmed via a live check that a
# single size=200 request returns every event in one page even for
# Westminster's ~160/day, so no pagination is needed in practice.
FULL_LIST_SIZE = 200

# Calibrated against live counts (checked 2026-08-28: 3-109 events found
# today within 2km across 5 central zones - South Bank's West End-adjacent
# venue density dwarfing everywhere else). A log scale keeps that spread
# meaningful instead of either saturating everything or flattening the low
# end, which a linear cap would do given the ~35x range between zones.
_DENSITY_LOG_CAP = 150

_CACHE_TTL_SECONDS = 1200
_cache: dict[tuple[float, float], tuple["EventReading", float]] = {}
_all_events_cache: dict[tuple[float, float], tuple[list[str], float]] = {}
_request_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)


class EventReading(NamedTuple):
    density: float  # 0-1
    description: str  # plain-language summary, naming an event when there is one
    count: int  # true total found today within range (can exceed len(events))
    events: list[str]  # up to SAMPLE_SIZE formatted "name — venue, time" listings


async def fetch_event_density(lat: float, lng: float) -> EventReading | None:
    """Return an event reading for a point, or None if unavailable/unconfigured."""
    if not settings.ticketmaster_api_key:
        return None

    key = (round(lat, 3), round(lng, 3))
    now = time.monotonic()

    cached = _cache.get(key)
    if cached is not None and now - cached[1] < _CACHE_TTL_SECONDS:
        return cached[0]

    page = await _fetch_events_page(lat, lng, SAMPLE_SIZE)
    if page is None:
        return None
    sample_events, total = page

    reading = EventReading(
        density=_density_from_count(total),
        description=_describe(total, sample_events),
        count=total,
        events=[_format_event(e) for e in sample_events],
    )
    _cache[key] = (reading, now)
    return reading


async def fetch_all_events(lat: float, lng: float) -> list[str] | None:
    """Fetch every event today within range for one zone, on demand.

    Unlike fetch_event_density's SAMPLE_SIZE-capped list (built for the
    every-30-seconds, all-33-zones poll), this is only called for one zone
    at a time when a user actually asks to see its full event list.
    """
    if not settings.ticketmaster_api_key:
        return None

    key = (round(lat, 3), round(lng, 3))
    now = time.monotonic()

    cached = _all_events_cache.get(key)
    if cached is not None and now - cached[1] < _CACHE_TTL_SECONDS:
        return cached[0]

    page = await _fetch_events_page(lat, lng, FULL_LIST_SIZE)
    if page is None:
        return None
    all_events, _total = page

    formatted = [_format_event(e) for e in all_events]
    _all_events_cache[key] = (formatted, now)
    return formatted


async def _fetch_events_page(lat: float, lng: float, size: int) -> tuple[list[dict], int] | None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    params = {
        "latlong": f"{lat},{lng}",
        "radius": str(SEARCH_RADIUS_KM),
        "unit": "km",
        "startDateTime": f"{today}T00:00:00Z",
        "endDateTime": f"{today}T23:59:59Z",
        "size": str(size),
        "apikey": settings.ticketmaster_api_key,
    }

    async with _request_semaphore, httpx.AsyncClient(timeout=8.0) as client:
        try:
            resp = await client.get(DISCOVERY_EVENTS_URL, params=params)
            resp.raise_for_status()
            body = resp.json()
        except (httpx.HTTPError, ValueError):
            return None

    events = body.get("_embedded", {}).get("events", [])
    total = body.get("page", {}).get("totalElements", 0)
    return events, total


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


def _format_event(event: dict) -> str:
    name = event.get("name", "Untitled event")
    venues = event.get("_embedded", {}).get("venues") or []
    venue = venues[0].get("name") if venues else None

    start = event.get("dates", {}).get("start", {})
    when = start.get("localDate", "")
    time_str = start.get("localTime")
    if time_str:
        when = f"{when} {time_str[:5]}".strip()

    detail = " · ".join(bit for bit in (venue, when) if bit)
    return f"{name} — {detail}" if detail else name
