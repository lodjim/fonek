from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FONEK_")

    data_dir: Path = Path("data")
    poll_interval_min: int = 15

    @property
    def db_path(self) -> Path:
        return self.data_dir / "fonek.db"

    @property
    def account_path(self) -> Path:
        return self.data_dir / "account.json"

    @property
    def anisette_libs_path(self) -> Path:
        return self.data_dir / "anisette_libs"


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
