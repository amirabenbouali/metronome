"""Live transit-delay signal via TfL's Tube line status feed.

Free, no API key required. See:
https://api.tfl.gov.uk/swagger/ui/index.html#!/Line

Each zone maps to the Tube line(s) that actually serve it; delay is derived
from TfL's own statusSeverity (0-20+ scale covering many special states, but
in practice real-time queries return values in roughly the 0-10 range for
genuine service issues - 10 is "Good Service", lower is worse).
"""

import time

import httpx

TFL_LINE_STATUS_URL = "https://api.tfl.gov.uk/Line/Mode/tube/Status"
USER_AGENT = "Metronome/0.1 (+https://github.com/amirabenbouali/metronome)"

# zone slug -> Tube line ids that actually serve that area
ZONE_LINES: dict[str, list[str]] = {
    "camden": ["northern"],
    "shoreditch": ["central", "northern"],
    "south-bank": ["jubilee", "northern"],
    "canary-wharf": ["jubilee"],
    "paddington": ["bakerloo", "circle", "district", "hammersmith-city"],
}

_CACHE_TTL_SECONDS = 120  # service status can change quickly
_cache: tuple[dict[str, float], float] | None = None  # {line_id: severity} -> fetched_at


async def fetch_transit_delay(slug: str) -> float | None:
    """Return a 0-1 transit delay score for a zone, or None if unavailable."""
    lines = ZONE_LINES.get(slug)
    if not lines:
        return None

    severities = await _fetch_line_severities()
    if severities is None:
        return None

    matched = [severities[line] for line in lines if line in severities]
    if not matched:
        return None

    avg_status_severity = sum(matched) / len(matched)
    # 10 = Good Service -> 0 delay; each point below scales delay up.
    return round(min(max((10 - avg_status_severity) / 10, 0.0), 1.0), 2)


async def _fetch_line_severities() -> dict[str, float] | None:
    global _cache
    now = time.monotonic()

    if _cache is not None and now - _cache[1] < _CACHE_TTL_SECONDS:
        return _cache[0]

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
        worst = min(s["statusSeverity"] for s in statuses)
        severities[line["id"]] = worst

    _cache = (severities, now)
    return severities
