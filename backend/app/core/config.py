from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Metronome"
    environment: str = "local"
    database_url: str = "postgresql+asyncpg://metronome:metronome@localhost:5432/metronome"
    cors_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
