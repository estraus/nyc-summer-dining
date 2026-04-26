from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
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
    resy_api_key: str = ""
    resy_auth_token: str = ""
    cookie_secure: bool = False
    login_rate_limit: int = 10
    login_rate_window_seconds: int = 3600
    search_rate_limit: int = 30
    search_rate_window_seconds: int = 3600

    @model_validator(mode="after")
    def _reject_insecure_prod_defaults(self) -> "Settings":
        if not self.cookie_secure:
            return self
        errors: list[str] = []
        if self.cookie_signing_key == "dev-insecure-change-me":
            errors.append(
                "COOKIE_SIGNING_KEY is the dev placeholder — "
                "generate a real key with: openssl rand -hex 32"
            )
        if not self.shared_password_hash:
            errors.append(
                "SHARED_PASSWORD_HASH is empty — the app would be accessible without a password"
            )
        if errors:
            bullet = "\n  • "
            raise ValueError(
                f"Refusing to start: COOKIE_SECURE=true with insecure settings:{bullet}"
                + bullet.join(errors)
            )
        return self

    @property
    def db_path(self) -> Path:
        return self.database_path or (self.data_dir / "restaurants.db")

    @property
    def active_llm_model(self) -> str:
        if self.llm_provider == "nvidia":
            return self.nvidia_model
        return self.llm_model


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
