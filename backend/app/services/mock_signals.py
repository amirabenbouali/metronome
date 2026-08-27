"""Placeholder per-zone signals until real ingestion is wired up.

Zone geometry/identity now live in Postgres (see `zones` table, seeded via
scripts/seed_zones.py); this keeps just the signal side of the mock data,
keyed by zone slug.
"""

from app.schemas.zone import ZoneSignals

MOCK_SIGNALS: dict[str, ZoneSignals] = {
    "midtown": ZoneSignals(
        traffic_congestion=0.82, transit_delay=0.55, weather_severity=0.1, event_density=0.7
    ),
    "downtown": ZoneSignals(
        traffic_congestion=0.45, transit_delay=0.3, weather_severity=0.1, event_density=0.2
    ),
    "upper-west-side": ZoneSignals(
        traffic_congestion=0.3, transit_delay=0.2, weather_severity=0.1, event_density=0.15
    ),
    "williamsburg": ZoneSignals(
        traffic_congestion=0.4, transit_delay=0.45, weather_severity=0.1, event_density=0.6
    ),
    "long-island-city": ZoneSignals(
        traffic_congestion=0.25, transit_delay=0.35, weather_severity=0.1, event_density=0.1
    ),
}

# Used for zones that exist in the DB but have no mock signal entry yet.
DEFAULT_SIGNALS = ZoneSignals(
    traffic_congestion=0.2, transit_delay=0.2, weather_severity=0.1, event_density=0.1
)
