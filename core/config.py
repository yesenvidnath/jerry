"""Environment-backed application settings for Jerry."""

from dataclasses import dataclass
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = "Jerry"
    app_env: str = "development"
    api_host: str = "127.0.0.1"
    api_port: int = 8010
    log_level: str = "INFO"
    api_base_url: str = "http://127.0.0.1:8010"
    rate_limit_capacity: int = 20
    rate_limit_refill_per_minute: float = 10.0
    retrieval_timeout_seconds: float = 15.0
    llm_timeout_seconds: float = 30.0
    tool_timeout_seconds: float = 3.0

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_name=os.getenv("APP_NAME", "Jerry"),
            app_env=os.getenv("APP_ENV", "development"),
            api_host=os.getenv("API_HOST", "127.0.0.1"),
            api_port=int(os.getenv("API_PORT", "8010")),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            api_base_url=os.getenv("API_BASE_URL", "http://127.0.0.1:8010").rstrip("/"),
            rate_limit_capacity=max(1, int(os.getenv("RATE_LIMIT_CAPACITY", "20"))),
            rate_limit_refill_per_minute=max(0.1, float(os.getenv("RATE_LIMIT_REFILL_PER_MINUTE", "10"))),
            retrieval_timeout_seconds=max(0.1, float(os.getenv("RETRIEVAL_TIMEOUT_SECONDS", "15"))),
            llm_timeout_seconds=max(0.1, float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))),
            tool_timeout_seconds=max(0.1, float(os.getenv("TOOL_TIMEOUT_SECONDS", "3"))),
        )


settings = Settings.from_env()
