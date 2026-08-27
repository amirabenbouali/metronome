from typing import Any

from pydantic import BaseModel, Field


class ZoneSignals(BaseModel):
    """Normalized 0-1 inputs feeding the per-zone pulse score."""

    traffic_congestion: float = Field(ge=0, le=1)
    transit_delay: float = Field(ge=0, le=1)
    weather_severity: float = Field(ge=0, le=1)
    event_density: float = Field(ge=0, le=1)


class ZoneScoreOut(BaseModel):
    id: str
    name: str
    score: float
    signals: ZoneSignals
    geometry: dict[str, Any]
