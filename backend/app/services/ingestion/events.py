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
"""

import math
import time
from datetime import datetime, timezone

import httpx

from app.core.config import settings

DISCOVERY_EVENTS_URL = "https://app.ticketmaster.com/discovery/v2/events.json"
SEARCH_RADIUS_KM = 2

# Calibrated against live counts (checked 2026-08-28: 3-109 events found
# today within 2km across the 5 zones - South Bank's West End-adjacent
# venue density dwarfing everywhere else). A log scale keeps that spread
# meaningful instead of either saturating everything or flattening the low
# end, which a linear cap would do given the ~35x range between zones.
_DENSITY_LOG_CAP = 150

_CACHE_TTL_SECONDS = 600
_cache: dict[tuple[float, float], tuple[float, float]] = {}  # (lat, lng) -> (density, fetched_at)


async def fetch_event_density(lat: float, lng: float) -> float | None:
    """Return a 0-1 event density score for a point, or None if unavailable/unconfigured."""
    if not settings.ticketmaster_api_key:
        return None

    key = (round(lat, 3), round(lng, 3))
    now = time.monotonic()

    cached = _cache.get(key)
    if cached is not None and now - cached[1] < _CACHE_TTL_SECONDS:
        return cached[0]

    density = await _fetch_live_density(lat, lng)
    if density is not None:
        _cache[key] = (density, now)
    return density


async def _fetch_live_density(lat: float, lng: float) -> float | None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    params = {
        "latlong": f"{lat},{lng}",
        "radius": str(SEARCH_RADIUS_KM),
        "unit": "km",
        "startDateTime": f"{today}T00:00:00Z",
        "endDateTime": f"{today}T23:59:59Z",
        "size": "1",  # only the total count is needed, not the events themselves
        "apikey": settings.ticketmaster_api_key,
    }

    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(DISCOVERY_EVENTS_URL, params=params)
            resp.raise_for_status()
            total = resp.json().get("page", {}).get("totalElements", 0)
        except (httpx.HTTPError, ValueError, KeyError):
            return None

    return _density_from_count(total)


def _density_from_count(count: int) -> float:
    density = math.log10(count + 1) / math.log10(_DENSITY_LOG_CAP + 1)
    return round(min(max(density, 0.0), 1.0), 2)
