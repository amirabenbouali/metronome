import json

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.zone import Zone
from app.schemas.zone import ZoneScoreOut
from app.services.mock_signals import DEFAULT_SIGNALS, MOCK_SIGNALS
from app.services.scoring import compute_zone_score

router = APIRouter(tags=["zones"])


@router.get("/zones", response_model=list[ZoneScoreOut])
async def list_zones(db: AsyncSession = Depends(get_db)) -> list[ZoneScoreOut]:
    """Return per-zone pulse scores.

    Zone geometry/identity come from Postgres; signals are still hardcoded
    mock values until real ingestion adapters are wired up.
    """
    stmt = select(Zone, func.ST_AsGeoJSON(Zone.geom)).order_by(Zone.name)
    result = await db.execute(stmt)

    zones = []
    for zone, geojson in result.all():
        signals = MOCK_SIGNALS.get(zone.slug, DEFAULT_SIGNALS)
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
