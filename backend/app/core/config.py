from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Metronome"
    environment: str = "local"
    database_url: str = "postgresql+asyncpg://metronome:metronome@localhost:5432/metronome"
    # asyncpg doesn't understand libpq-style ?sslmode=require in the URL -
    # hosted Postgres (Supabase, etc.) needs SSL passed via connect_args
    # instead, so this is a separate flag rather than a URL query param.
    database_ssl: bool = False
    # Comma-separated rather than a JSON list: far easier to paste into a
    # hosting dashboard's plain-text env var field than JSON array syntax.
    # Aliased so the env var stays the intuitive CORS_ORIGINS.
    cors_origins_raw: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")
    # Ticketmaster Discovery API key for the events ingestion adapter.
    # Optional - event_density falls back to a mock value if unset.
    ticketmaster_api_key: str = ""

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]


settings = Settings()
