"""Fallback signal values for when a live ingestion fetch fails.

All four signals are live in normal use (see app/services/ingestion/). With
33 zones (every London borough), per-zone mock tuning stopped making sense -
this is just a neutral fallback, not a stand-in for real per-area data.
"""

from app.schemas.zone import SignalDetails, ZoneSignals

DEFAULT_SIGNALS = ZoneSignals(
    traffic_congestion=0.2, transit_delay=0.2, weather_severity=0.1, event_density=0.1
)

DEFAULT_DETAILS = SignalDetails(
    traffic="Live data unavailable right now",
    transit="Live data unavailable right now",
    weather="Live data unavailable right now",
    events="Live data unavailable right now",
)
