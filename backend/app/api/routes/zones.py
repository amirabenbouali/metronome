import asyncio
import json

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.zone import Zone
from app.schemas.zone import ZoneScoreOut
from app.services.ingestion.weather import fetch_weather_severity
from app.services.mock_signals import DEFAULT_SIGNALS, MOCK_SIGNALS
from app.services.scoring import compute_zone_score

router = APIRouter(tags=["zones"])


@router.get("/zones", response_model=list[ZoneScoreOut])
async def list_zones(db: AsyncSession = Depends(get_db)) -> list[ZoneScoreOut]:
    """Return per-zone pulse scores.

    Zone geometry/identity come from Postgres. weather_severity is live, via
    the NWS API; the other three signals are still hardcoded mock values
    until their own ingestion adapters are wired up.
    """
    stmt = select(
        Zone,
        func.ST_AsGeoJSON(Zone.geom),
        func.ST_Y(func.ST_Centroid(Zone.geom)),
        func.ST_X(func.ST_Centroid(Zone.geom)),
    ).order_by(Zone.name)
    rows = (await db.execute(stmt)).all()

    live_weather = await asyncio.gather(
        *(fetch_weather_severity(lat, lng) for _, _, lat, lng in rows)
    )

    zones = []
    for (zone, geojson, _lat, _lng), weather_severity in zip(rows, live_weather):
        base_signals = MOCK_SIGNALS.get(zone.slug, DEFAULT_SIGNALS)
        signals = base_signals.model_copy(
            update={
                "weather_severity": weather_severity
                if weather_severity is not None
                else base_signals.weather_severity
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
