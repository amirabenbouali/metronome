import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from geoalchemy2.alembic_helpers import include_object as geoalchemy2_include_object
from geoalchemy2.alembic_helpers import render_item, writer

from app.core.config import settings
from app.db.base import Base
from app.models import zone  # noqa: F401  (registers Zone with Base.metadata)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Tables belonging to the postgis_tiger_geocoder and postgis_topology extensions.
# Their `tiger`/`topology` schemas are on this DB's search_path, so plain
# (schema=None) reflection flattens them in alongside our own tables with no
# schema attribute to filter on - so we exclude by name instead.
_EXTENSION_TABLES = {
    "topology", "layer", "featnames", "geocode_settings", "geocode_settings_default",
    "direction_lookup", "secondary_unit_lookup", "state_lookup", "street_type_lookup",
    "place_lookup", "county_lookup", "countysub_lookup", "zip_lookup_all", "zip_lookup_base",
    "zip_lookup", "county", "state", "place", "zip_state", "zip_state_loc", "cousub",
    "edges", "addrfeat", "addr", "zcta5", "tabblock20", "faces", "loader_platform",
    "loader_variables", "loader_lookuptables", "tract", "tabblock", "bg",
    "pagc_gaz", "pagc_lex", "pagc_rules",
}


def include_object(obj, name, obj_type, reflected, compare_to):
    """Skip PostGIS's own tiger/topology extension tables and public.spatial_ref_sys."""
    if obj_type == "table" and name in _EXTENSION_TABLES:
        return False
    return geoalchemy2_include_object(obj, name, obj_type, reflected, compare_to)

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        render_item=render_item,
        process_revision_directives=writer,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        render_item=render_item,
        process_revision_directives=writer,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    # See app/db/session.py: asyncpg takes SSL via connect_args, not a
    # ?sslmode= query param, so hosted Postgres (Supabase, etc.) needs this
    # passed explicitly here too - async_engine_from_config has no idea
    # about our own database_ssl setting.
    connect_args = {"ssl": "require"} if settings.database_ssl else {}
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
