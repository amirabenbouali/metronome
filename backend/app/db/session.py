from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# See config.py: asyncpg takes SSL via connect_args, not a ?sslmode= query param.
connect_args = {"ssl": "require"} if settings.database_ssl else {}

engine = create_async_engine(
    settings.database_url, echo=False, future=True, connect_args=connect_args
)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
