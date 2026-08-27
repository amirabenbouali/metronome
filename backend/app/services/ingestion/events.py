"""Live event-density signal via NYC Open Data's permitted events dataset.

Free, no API key required. See:
https://data.cityofnewyork.us/City-Government/NYC-Permitted-Event-Information/bkfu-528j

The dataset gives events by borough + community board rather than
coordinates, so each zone is mapped to the community board that covers it.
This is a coarser match than point-in-polygon, but a reasonable proxy until
zones carry their own precise district metadata.
"""

import time
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

SOCRATA_BASE = "https://data.cityofnewyork.us/resource/bkfu-528j.json"
USER_AGENT = "Metronome/0.1 (+https://github.com/amirabenbouali/metronome)"
NYC_TZ = ZoneInfo("America/New_York")

# zone slug -> (event_borough, community_board number as used in the dataset)
ZONE_COMMUNITY_BOARDS: dict[str, tuple[str, str]] = {
    "midtown": ("Manhattan", "5"),
    "downtown": ("Manhattan", "1"),
    "upper-west-side": ("Manhattan", "7"),
    "williamsburg": ("Brooklyn", "1"),
    "long-island-city": ("Queens", "2"),
}

_CACHE_TTL_SECONDS = 600
_cache: dict[tuple[str, str], tuple[float, float]] = {}  # (borough, board) -> (density, fetched_at)


async def fetch_event_density(borough: str, board: str) -> float | None:
    """Return a 0-1 event density score for a borough/community-board, or None if unavailable."""
    key = (borough, board)
    now = time.monotonic()

    cached = _cache.get(key)
    if cached is not None and now - cached[1] < _CACHE_TTL_SECONDS:
        return cached[0]

    density = await _fetch_live_density(borough, board)
    if density is not None:
        _cache[key] = (density, now)
    return density


async def _fetch_live_density(borough: str, board: str) -> float | None:
    now_local = datetime.now(NYC_TZ).replace(tzinfo=None).isoformat(timespec="seconds")
    where = (
        f"event_borough='{borough}' "
        f"AND community_board like '%{board},%' "
        f"AND start_date_time <= '{now_local}' "
        f"AND end_date_time >= '{now_local}'"
    )
    params = {"$where": where, "$select": "count(*) as event_count"}
    headers = {"User-Agent": USER_AGENT}

    async with httpx.AsyncClient(timeout=5.0, headers=headers) as client:
        try:
            resp = await client.get(SOCRATA_BASE, params=params)
            resp.raise_for_status()
            rows = resp.json()
            event_count = int(rows[0]["event_count"]) if rows else 0
        except (httpx.HTTPError, KeyError, IndexError, ValueError):
            return None

    return _density_from_count(event_count)


def _density_from_count(count: int) -> float:
    # NYC's permitted-events feed includes routine park closures/maintenance
    # alongside actual events, so raw counts run high (5-30+ is typical for
    # a Manhattan community board on an ordinary day). Calibrated against
    # live observed counts rather than a guess: 20+ concurrent permits is
    # treated as maximally busy.
    return round(min(count / 20.0, 1.0), 2)
