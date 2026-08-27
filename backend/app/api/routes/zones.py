from fastapi import APIRouter

from app.schemas.zone import ZoneScoreOut
from app.services.mock_data import MOCK_ZONES, mock_zone_geometry
from app.services.scoring import compute_zone_score

router = APIRouter(tags=["zones"])


@router.get("/zones", response_model=list[ZoneScoreOut])
async def list_zones() -> list[ZoneScoreOut]:
    """Return per-zone pulse scores.

    Backed by hardcoded mock signals for now; once ingestion + Postgres are
    wired up this will read real zone geometries and live signal data.
    """
    zones = []
    for zone in MOCK_ZONES:
        lng, lat = zone["center"]
        zones.append(
            ZoneScoreOut(
                id=zone["id"],
                name=zone["name"],
                score=compute_zone_score(zone["signals"]),
                signals=zone["signals"],
                geometry=mock_zone_geometry(lng, lat),
            )
        )
    return zones
