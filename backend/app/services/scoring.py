from app.schemas.zone import ZoneSignals

# Relative contribution of each signal to the overall pulse score. Traffic and
# events dominate since they're the most volatile minute-to-minute inputs;
# weather is the least (it moves slowly and mostly acts through the others).
SIGNAL_WEIGHTS = {
    "traffic_congestion": 0.35,
    "transit_delay": 0.25,
    "weather_severity": 0.15,
    "event_density": 0.25,
}


def compute_zone_score(signals: ZoneSignals) -> float:
    """Combine normalized 0-1 signals into a 0-100 pulse score."""
    weighted = (
        signals.traffic_congestion * SIGNAL_WEIGHTS["traffic_congestion"]
        + signals.transit_delay * SIGNAL_WEIGHTS["transit_delay"]
        + signals.weather_severity * SIGNAL_WEIGHTS["weather_severity"]
        + signals.event_density * SIGNAL_WEIGHTS["event_density"]
    )
    return round(weighted * 100, 1)
