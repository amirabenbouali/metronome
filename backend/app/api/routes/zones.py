import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.zone import Zone
from app.schemas.zone import ZoneScoreOut
from app.services.ingestion.events import fetch_all_events, fetch_event_density
from app.services.ingestion.traffic import fetch_traffic_congestion
from app.services.ingestion.transit import fetch_transit_delay
from app.services.ingestion.weather import fetch_weather
from app.services.mock_signals import DEFAULT_DETAILS, DEFAULT_SIGNALS
from app.services.scoring import compute_zone_score

router = APIRouter(tags=["zones"])


@router.get("/zones", response_model=list[ZoneScoreOut])
async def list_zones(db: AsyncSession = Depends(get_db)) -> list[ZoneScoreOut]:
    """Return per-zone pulse scores.

    Zone geometry/identity come from Postgres (all 32 London boroughs + City
    of London). weather (Open-Meteo), traffic_congestion (TfL road status),
    transit_delay (TfL line status, all rail modes), and event_density
    (Ticketmaster Discovery API, when TICKETMASTER_API_KEY is configured)
    are all live and fall back to a mocked value per-signal if their fetch
    fails or isn't configured. Each signal also carries a plain-language
    `details` sentence naming what's actually behind its number.
    """
    stmt = select(
        Zone,
        func.ST_AsGeoJSON(Zone.geom),
        func.ST_Y(func.ST_Centroid(Zone.geom)),
        func.ST_X(func.ST_Centroid(Zone.geom)),
        func.ST_YMin(Zone.geom),
        func.ST_YMax(Zone.geom),
        func.ST_XMin(Zone.geom),
        func.ST_XMax(Zone.geom),
    ).order_by(Zone.name)
    rows = (await db.execute(stmt)).all()

    live_weather, live_traffic, live_transit, live_events = await asyncio.gather(
        asyncio.gather(*(fetch_weather(lat, lng) for _, _, lat, lng, *_ in rows)),
        asyncio.gather(
            *(
                fetch_traffic_congestion((min_lat, max_lat, min_lng, max_lng))
                for _, _, _, _, min_lat, max_lat, min_lng, max_lng in rows
            )
        ),
        asyncio.gather(
            *(
                fetch_transit_delay((min_lat, max_lat, min_lng, max_lng))
                for _, _, _, _, min_lat, max_lat, min_lng, max_lng in rows
            )
        ),
        asyncio.gather(*(fetch_event_density(lat, lng) for _, _, lat, lng, *_ in rows)),
    )

    zones = []
    for (
        (zone, geojson, *_bbox),
        weather,
        traffic,
        transit,
        events,
    ) in zip(rows, live_weather, live_traffic, live_transit, live_events):
        signals = DEFAULT_SIGNALS.model_copy(
            update={
                "weather_severity": weather.severity if weather else DEFAULT_SIGNALS.weather_severity,
                "traffic_congestion": traffic.congestion if traffic else DEFAULT_SIGNALS.traffic_congestion,
                "transit_delay": transit.delay if transit else DEFAULT_SIGNALS.transit_delay,
                "event_density": events.density if events else DEFAULT_SIGNALS.event_density,
            }
        )
        details = DEFAULT_DETAILS.model_copy(
            update={
                "weather": weather.description if weather else DEFAULT_DETAILS.weather,
                "traffic": traffic.description if traffic else DEFAULT_DETAILS.traffic,
                "transit": transit.description if transit else DEFAULT_DETAILS.transit,
                "events": events.description if events else DEFAULT_DETAILS.events,
            }
        )
        zones.append(
            ZoneScoreOut(
                id=zone.slug,
                name=zone.name,
                score=compute_zone_score(signals),
                signals=signals,
                details=details,
                event_count=events.count if events else 0,
                events=events.events if events else [],
                geometry=json.loads(geojson),
            )
        )
    return zones


@router.get("/zones/{slug}/events", response_model=list[str])
async def get_zone_events(slug: str, db: AsyncSession = Depends(get_db)) -> list[str]:
    """Return every event today near one zone, fetched fresh on demand.

    The main /zones list only ever carries a small sample (see
    ingestion/events.py's SAMPLE_SIZE) since it fans out to all 33 zones
    every 30-second poll - this exists for "show me everything" for one
    zone at a time, which a single size=200 Ticketmaster request covers in
    practice (confirmed live: Westminster's ~160/day fit on one page).
    """
    stmt = select(
        func.ST_Y(func.ST_Centroid(Zone.geom)), func.ST_X(func.ST_Centroid(Zone.geom))
    ).where(Zone.slug == slug)
    row = (await db.execute(stmt)).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Unknown zone: {slug}")

    lat, lng = row
    events = await fetch_all_events(lat, lng)
    return events or []
