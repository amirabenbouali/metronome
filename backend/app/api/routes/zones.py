import asyncio
import json

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.zone import Zone
from app.schemas.zone import ZoneScoreOut
from app.services.ingestion.events import fetch_event_density
from app.services.ingestion.traffic import fetch_traffic_congestion
from app.services.ingestion.transit import fetch_transit_delay
from app.services.ingestion.weather import fetch_weather_severity
from app.services.mock_signals import DEFAULT_SIGNALS, MOCK_SIGNALS
from app.services.scoring import compute_zone_score

router = APIRouter(tags=["zones"])


@router.get("/zones", response_model=list[ZoneScoreOut])
async def list_zones(db: AsyncSession = Depends(get_db)) -> list[ZoneScoreOut]:
    """Return per-zone pulse scores.

    Zone geometry/identity come from Postgres. weather_severity (Open-Meteo),
    traffic_congestion (TfL road status), transit_delay (TfL Tube line
    status), and event_density (Ticketmaster Discovery API, when
    TICKETMASTER_API_KEY is configured) are all live and fall back to a
    mocked value per-signal if their fetch fails or isn't configured.
    """
    stmt = select(
        Zone,
        func.ST_AsGeoJSON(Zone.geom),
        func.ST_Y(func.ST_Centroid(Zone.geom)),
        func.ST_X(func.ST_Centroid(Zone.geom)),
    ).order_by(Zone.name)
    rows = (await db.execute(stmt)).all()

    live_weather, live_traffic, live_transit, live_events = await asyncio.gather(
        asyncio.gather(*(fetch_weather_severity(lat, lng) for _, _, lat, lng in rows)),
        asyncio.gather(*(fetch_traffic_congestion(lat, lng) for _, _, lat, lng in rows)),
        asyncio.gather(*(fetch_transit_delay(zone.slug) for zone, *_ in rows)),
        asyncio.gather(*(fetch_event_density(lat, lng) for _, _, lat, lng in rows)),
    )

    zones = []
    for (
        (zone, geojson, _lat, _lng),
        weather_severity,
        traffic_congestion,
        transit_delay,
        event_density,
    ) in zip(rows, live_weather, live_traffic, live_transit, live_events):
        base_signals = MOCK_SIGNALS.get(zone.slug, DEFAULT_SIGNALS)
        signals = base_signals.model_copy(
            update={
                "weather_severity": weather_severity
                if weather_severity is not None
                else base_signals.weather_severity,
                "traffic_congestion": traffic_congestion
                if traffic_congestion is not None
                else base_signals.traffic_congestion,
                "transit_delay": transit_delay
                if transit_delay is not None
                else base_signals.transit_delay,
                "event_density": event_density
                if event_density is not None
                else base_signals.event_density,
            }
        )
        zones.append(
            ZoneScoreOut(
                id=zone.slug,
                name=zone.name,
                score=compute_zone_score(signals),
                signals=signals,
                geometry=json.loads(geojson),
            )
        )
    return zones
