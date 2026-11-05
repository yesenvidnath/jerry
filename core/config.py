"""Environment-backed application settings for the Jerry demo."""

from dataclasses import dataclass
import os


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = "Jerry"
    app_env: str = "development"
    api_host: str = "127.0.0.1"
    api_port: int = 8010
    log_level: str = "INFO"
    api_base_url: str = "http://127.0.0.1:8010"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_name=os.getenv("APP_NAME", "Jerry"),
            app_env=os.getenv("APP_ENV", "development"),
            api_host=os.getenv("API_HOST", "127.0.0.1"),
            api_port=int(os.getenv("API_PORT", "8010")),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            api_base_url=os.getenv("API_BASE_URL", "http://127.0.0.1:8010").rstrip("/"),
        )


settings = Settings.from_env()


