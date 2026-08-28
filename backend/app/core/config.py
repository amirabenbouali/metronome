from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Metronome"
    environment: str = "local"
    database_url: str = "postgresql+asyncpg://metronome:metronome@localhost:5432/metronome"
    cors_origins: list[str] = ["http://localhost:5173"]
    # Ticketmaster Discovery API key for the events ingestion adapter.
    # Optional - event_density falls back to a mock value if unset.
    ticketmaster_api_key: str = ""


settings = Settings()
