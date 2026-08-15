"""Settings loaded from the environment (see .env.example)."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DG_", env_file=".env", extra="ignore")

    db_host: str = "localhost"
    db_port: int = 5433
    db_name: str = "garage"
    db_user: str = "garage"
    db_password: str = "garage"

    raw_dir: Path = Path("./data/raw")
    vehicle_vin: str = "1FADP3L94HL223134"
    # Regenerate MODS.md + garage.json automatically after an approval so the
    # published dashboard stays current. Set DG_AUTO_EXPORT=0 to disable.
    auto_export: bool = True

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
settings.raw_dir.mkdir(parents=True, exist_ok=True)
