"""Seed the zones table with placeholder geometry for local development.

Usage (from backend/, with the venv active and Postgres reachable):
    python -m scripts.seed_zones
"""

import asyncio

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert

from app.db.session import async_session_factory
from app.models.zone import Zone

HALF_SIZE = 0.006

ZONES = [
    {"slug": "camden", "name": "Camden", "center": (-0.1426, 51.5390)},
    {"slug": "shoreditch", "name": "Shoreditch", "center": (-0.0777, 51.5229)},
    {"slug": "south-bank", "name": "South Bank", "center": (-0.1097, 51.5045)},
    {"slug": "canary-wharf", "name": "Canary Wharf", "center": (-0.0235, 51.5054)},
    {"slug": "paddington", "name": "Paddington", "center": (-0.1755, 51.5154)},
]

_CURRENT_SLUGS = {zone["slug"] for zone in ZONES}


def square_ewkt(center_lng: float, center_lat: float, half_size: float = HALF_SIZE) -> str:
    corners = [
        (center_lng - half_size, center_lat - half_size),
        (center_lng + half_size, center_lat - half_size),
        (center_lng + half_size, center_lat + half_size),
        (center_lng - half_size, center_lat + half_size),
        (center_lng - half_size, center_lat - half_size),
    ]
    ring = ", ".join(f"{lng} {lat}" for lng, lat in corners)
    return f"SRID=4326;POLYGON(({ring}))"


async def seed() -> None:
    async with async_session_factory() as session:
        # Drop any zones from a previous demo city (e.g. the original NYC
        # set) so the table only ever holds the current ZONES list.
        await session.execute(delete(Zone).where(Zone.slug.not_in(_CURRENT_SLUGS)))

        for zone in ZONES:
            lng, lat = zone["center"]
            stmt = (
                insert(Zone)
                .values(slug=zone["slug"], name=zone["name"], geom=square_ewkt(lng, lat))
                .on_conflict_do_update(
                    index_elements=[Zone.slug],
                    set_={"name": zone["name"], "geom": square_ewkt(lng, lat)},
                )
            )
            await session.execute(stmt)
        await session.commit()
    print(f"Seeded {len(ZONES)} zones.")


if __name__ == "__main__":
    asyncio.run(seed())
