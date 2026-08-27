"""Seed the zones table with placeholder geometry for local development.

Usage (from backend/, with the venv active and Postgres reachable):
    python -m scripts.seed_zones
"""

import asyncio

from sqlalchemy.dialects.postgresql import insert

from app.db.session import async_session_factory
from app.models.zone import Zone

HALF_SIZE = 0.006

ZONES = [
    {"slug": "midtown", "name": "Midtown", "center": (-73.9840, 40.7549)},
    {"slug": "downtown", "name": "Downtown / Financial District", "center": (-74.0113, 40.7075)},
    {"slug": "upper-west-side", "name": "Upper West Side", "center": (-73.9773, 40.7870)},
    {"slug": "williamsburg", "name": "Williamsburg", "center": (-73.9571, 40.7143)},
    {"slug": "long-island-city", "name": "Long Island City", "center": (-73.9482, 40.7447)},
]


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
