"""Live weather signal via Open-Meteo.

Free, no API key required, and covers any location worldwide (unlike the US
National Weather Service used in this project's original NYC version). See:
https://open-meteo.com/en/docs
"""

import time

import httpx

OPEN_METEO_BASE = "https://api.open-meteo.com/v1/forecast"
USER_AGENT = "Metronome/0.1 (+https://github.com/amirabenbouali/metronome)"

_CACHE_TTL_SECONDS = 600
_cache: dict[tuple[float, float], tuple[float, float]] = {}  # (lat, lng) -> (severity, fetched_at)


async def fetch_weather_severity(lat: float, lng: float) -> float | None:
    """Return a 0-1 weather severity score for a point, or None if unavailable."""
    key = (round(lat, 2), round(lng, 2))
    now = time.monotonic()

    cached = _cache.get(key)
    if cached is not None and now - cached[1] < _CACHE_TTL_SECONDS:
        return cached[0]

    severity = await _fetch_live_severity(lat, lng)
    if severity is not None:
        _cache[key] = (severity, now)
    return severity


async def _fetch_live_severity(lat: float, lng: float) -> float | None:
    params = {
        "latitude": f"{lat:.4f}",
        "longitude": f"{lng:.4f}",
        "current": "temperature_2m,wind_speed_10m,wind_gusts_10m,precipitation",
    }
    headers = {"User-Agent": USER_AGENT}

    async with httpx.AsyncClient(timeout=5.0, headers=headers) as client:
        try:
            resp = await client.get(OPEN_METEO_BASE, params=params)
            resp.raise_for_status()
            current = resp.json()["current"]
        except (httpx.HTTPError, KeyError, TypeError):
            return None

    return _severity_from_current(current)


def _severity_from_current(current: dict) -> float:
    wind_kmh = current.get("wind_speed_10m") or 0.0
    gust_kmh = current.get("wind_gusts_10m") or 0.0
    precip_mm = current.get("precipitation") or 0.0
    temp_c = current.get("temperature_2m")

    wind_component = min(max(wind_kmh, gust_kmh) / 60.0, 1.0)  # 60 km/h+ is severe
    precip_component = min(precip_mm / 15.0, 1.0)  # 15mm/hr+ is severe
    temp_component = 0.0
    if temp_c is not None:
        if temp_c <= -10 or temp_c >= 35:
            temp_component = 1.0
        elif temp_c <= 0 or temp_c >= 30:
            temp_component = 0.5

    severity = max(wind_component, precip_component, temp_component)
    return round(min(severity, 1.0), 2)
