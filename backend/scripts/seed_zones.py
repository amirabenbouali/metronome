"""Seed the zones table with London's 32 boroughs + City of London.

Boundary source: backend/scripts/data/london_boroughs.geojson (33 features,
simple Polygons, bundled in the repo since this is stable reference data
that shouldn't depend on network access at seed time). Geometry is
simplified on insert via PostGIS - the raw boundaries are detailed enough
that every /zones response would otherwise ship ~1.3MB of coordinates to
the browser on every poll.

Usage (from backend/, with the venv active and Postgres reachable):
    python -m scripts.seed_zones
"""

import asyncio
import json
import re
from pathlib import Path

from sqlalchemy import delete, func
from sqlalchemy.dialects.postgresql import insert

from app.db.session import async_session_factory
from app.models.zone import Zone

BOUNDARIES_PATH = Path(__file__).parent / "data" / "london_boroughs.geojson"

# ~40m at London's latitude - keeps borough shapes recognizable while
# cutting the ~44,500 total source coordinate points down to a fraction of
# that, so /zones doesn't ship megabytes of geometry on every poll.
SIMPLIFY_TOLERANCE_DEGREES = 0.0004


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def ring_to_wkt(ring: list[list[float]]) -> str:
    return "(" + ", ".join(f"{lng} {lat}" for lng, lat in ring) + ")"


def polygon_ewkt(coordinates: list[list[list[float]]]) -> str:
    rings = ", ".join(ring_to_wkt(ring) for ring in coordinates)
    return f"SRID=4326;POLYGON({rings})"


def load_zones() -> list[dict]:
    with BOUNDARIES_PATH.open() as f:
        data = json.load(f)

    zones = []
    for feature in data["features"]:
        name = feature["properties"]["name"]
        geometry = feature["geometry"]
        if geometry["type"] != "Polygon":
            raise ValueError(f"Expected Polygon for {name!r}, got {geometry['type']!r}")
        zones.append({"slug": slugify(name), "name": name, "ewkt": polygon_ewkt(geometry["coordinates"])})
    return zones


async def seed() -> None:
    zones = load_zones()
    current_slugs = {zone["slug"] for zone in zones}

    async with async_session_factory() as session:
        # Drop any zones from a previous demo (e.g. the original NYC set,
        # or the 5 hand-picked London zones this replaces) so the table
        # only ever holds the current ZONES list.
        await session.execute(delete(Zone).where(Zone.slug.not_in(current_slugs)))

        for zone in zones:
            simplified_geom = func.ST_SimplifyPreserveTopology(
                func.ST_GeomFromEWKT(zone["ewkt"]), SIMPLIFY_TOLERANCE_DEGREES
            )
            stmt = (
                insert(Zone)
                .values(slug=zone["slug"], name=zone["name"], geom=simplified_geom)
                .on_conflict_do_update(
                    index_elements=[Zone.slug],
                    set_={"name": zone["name"], "geom": simplified_geom},
                )
            )
            await session.execute(stmt)
        await session.commit()
    print(f"Seeded {len(zones)} zones.")


if __name__ == "__main__":
    asyncio.run(seed())
