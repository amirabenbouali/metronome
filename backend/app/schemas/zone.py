from typing import Any

from pydantic import BaseModel, Field


class ZoneSignals(BaseModel):
    """Normalized 0-1 inputs feeding the per-zone pulse score."""

    traffic_congestion: float = Field(ge=0, le=1)
    transit_delay: float = Field(ge=0, le=1)
    weather_severity: float = Field(ge=0, le=1)
    event_density: float = Field(ge=0, le=1)


class SignalDetails(BaseModel):
    """One plain-language sentence per signal, explaining what's actually
    behind its number (which road, which line, etc.) rather than just the
    blended 0-1 value."""

    traffic: str
    transit: str
    weather: str
    events: str


class ZoneScoreOut(BaseModel):
    id: str
    name: str
    score: float
    signals: ZoneSignals
    details: SignalDetails
    geometry: dict[str, Any]
