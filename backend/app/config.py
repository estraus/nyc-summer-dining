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
    llm_provider: str = "anthropic"
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "minimaxai/minimax-m2.7"

    @property
    def db_path(self) -> Path:
        return self.database_path or (self.data_dir / "restaurants.db")

    @property
    def active_llm_model(self) -> str:
        if self.llm_provider == "nvidia":
            return self.nvidia_model
        return self.llm_model


def get_settings() -> Settings:
    return Settings()
