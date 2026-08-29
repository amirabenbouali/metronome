"""Live weather signal via Open-Meteo.

Free, no API key required, and covers any location worldwide (unlike the US
National Weather Service used in this project's original NYC version). See:
https://open-meteo.com/en/docs
"""

import time
from typing import NamedTuple

import httpx

OPEN_METEO_BASE = "https://api.open-meteo.com/v1/forecast"
USER_AGENT = "Metronome/0.1 (+https://github.com/amirabenbouali/metronome)"

_CACHE_TTL_SECONDS = 600
_cache: dict[tuple[float, float], tuple["WeatherReading", float]] = {}


class WeatherReading(NamedTuple):
    severity: float  # 0-1
    description: str  # plain-language summary, e.g. "21°C, calm winds"


async def fetch_weather(lat: float, lng: float) -> WeatherReading | None:
    """Return a weather reading for a point, or None if unavailable."""
    key = (round(lat, 2), round(lng, 2))
    now = time.monotonic()

    cached = _cache.get(key)
    if cached is not None and now - cached[1] < _CACHE_TTL_SECONDS:
        return cached[0]

    reading = await _fetch_live_reading(lat, lng)
    if reading is not None:
        _cache[key] = (reading, now)
    return reading


async def _fetch_live_reading(lat: float, lng: float) -> WeatherReading | None:
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

    return _reading_from_current(current)


def _reading_from_current(current: dict) -> WeatherReading:
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

    severity = round(min(max(wind_component, precip_component, temp_component), 1.0), 2)
    description = _describe(temp_c, wind_kmh, gust_kmh, precip_mm, severity)
    return WeatherReading(severity=severity, description=description)


def _describe(
    temp_c: float | None, wind_kmh: float, gust_kmh: float, precip_mm: float, severity: float
) -> str:
    temp_text = f"{round(temp_c)}°C" if temp_c is not None else "temperature unavailable"

    if severity < 0.15:
        return f"{temp_text}, calm conditions"
    if precip_mm >= 15 * severity and precip_mm > 2:
        return f"{temp_text}, rain ({precip_mm:.1f}mm/hr)"
    if max(wind_kmh, gust_kmh) / 60.0 >= severity - 0.01:
        return f"{temp_text}, windy ({round(max(wind_kmh, gust_kmh))} km/h gusts)"
    return f"{temp_text}, extreme temperature"
