"""Placeholder per-zone signals until real ingestion is wired up.

Zone geometry/identity now live in Postgres (see `zones` table, seeded via
scripts/seed_zones.py). traffic_congestion, transit_delay, and
weather_severity are live in production use (see app/services/ingestion/)
and these values only serve as a fallback when a live fetch fails.
event_density has no live source wired up yet (no free, no-signup London
events feed equivalent to NYC Open Data was found), so it's mocked for real,
not just as a fallback - values are a rough guess at each area's character
rather than measured data.
"""

from app.schemas.zone import ZoneSignals

MOCK_SIGNALS: dict[str, ZoneSignals] = {
    "camden": ZoneSignals(
        traffic_congestion=0.55, transit_delay=0.3, weather_severity=0.1, event_density=0.65
    ),
    "shoreditch": ZoneSignals(
        traffic_congestion=0.4, transit_delay=0.25, weather_severity=0.1, event_density=0.75
    ),
    "south-bank": ZoneSignals(
        traffic_congestion=0.35, transit_delay=0.2, weather_severity=0.1, event_density=0.6
    ),
    "canary-wharf": ZoneSignals(
        traffic_congestion=0.3, transit_delay=0.2, weather_severity=0.1, event_density=0.15
    ),
    "paddington": ZoneSignals(
        traffic_congestion=0.45, transit_delay=0.3, weather_severity=0.1, event_density=0.2
    ),
}

# Used for zones that exist in the DB but have no mock signal entry yet.
DEFAULT_SIGNALS = ZoneSignals(
    traffic_congestion=0.2, transit_delay=0.2, weather_severity=0.1, event_density=0.1
)
