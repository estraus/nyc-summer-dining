from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    data_dir: Path = REPO_ROOT / "data"
    frontend_dir: Path = REPO_ROOT / "frontend"
    database_path: Path | None = None
    shared_password_hash: str = ""
    cookie_signing_key: str = "dev-insecure-change-me"
    anthropic_api_key: str = ""
    llm_model: str = "claude-haiku-4-5-20251001"

    @property
    def db_path(self) -> Path:
        return self.database_path or (self.data_dir / "restaurants.db")


def get_settings() -> Settings:
    return Settings()
