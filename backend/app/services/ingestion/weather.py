"""Live weather signal via the US National Weather Service API.

api.weather.gov is free, requires no API key, and covers US locations - a
good fit since all current zones are in NYC. See:
https://www.weather.gov/documentation/services-web-api

This does a live 3-hop lookup (points -> nearest station -> latest
observation) per call, with a short in-memory cache so we're not hammering
NWS on every request. A production version would run this on a schedule and
persist results instead of fetching inline in the request path.
"""

import time

import httpx

NWS_BASE = "https://api.weather.gov"
# NWS asks that clients identify themselves; a repo URL is enough, no need
# for a personal contact.
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
    headers = {"User-Agent": USER_AGENT, "Accept": "application/geo+json"}
    async with httpx.AsyncClient(timeout=5.0, headers=headers) as client:
        try:
            points_resp = await client.get(f"{NWS_BASE}/points/{lat:.4f},{lng:.4f}")
            points_resp.raise_for_status()
            stations_url = points_resp.json()["properties"]["observationStations"]

            stations_resp = await client.get(stations_url)
            stations_resp.raise_for_status()
            features = stations_resp.json()["features"]
            if not features:
                return None
            station_id = features[0]["properties"]["stationIdentifier"]

            obs_resp = await client.get(f"{NWS_BASE}/stations/{station_id}/observations/latest")
            obs_resp.raise_for_status()
            properties = obs_resp.json()["properties"]
        except (httpx.HTTPError, KeyError, IndexError, TypeError):
            return None

    return _severity_from_observation(properties)


def _severity_from_observation(properties: dict) -> float:
    wind_kmh = (properties.get("windSpeed") or {}).get("value") or 0.0
    gust_kmh = (properties.get("windGust") or {}).get("value") or 0.0
    precip_mm = (properties.get("precipitationLastHour") or {}).get("value") or 0.0
    temp_c = (properties.get("temperature") or {}).get("value")

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
