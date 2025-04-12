from pydantic import field_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from typing import List


class Settings(BaseSettings):
    ENV: str
    DEEPSEEK_API_KEY: str
    DEEPSEEK_MODEL: str
    DEEPSEEK_BASE_URL: str
    MAX_CHAT_TURNS: int
    MAX_RETRIES: int
    E2B_API_KEY: str
    LOG_LEVEL: str
    DEBUG: bool
    REDIS_URL: str
    REDIS_MAX_CONNECTIONS: int

    model_config = SettingsConfigDict(env_file=".env.dev", env_file_encoding="utf-8")

    # @field_validator("CORS_ALLOW_ORIGINS", mode="before")
    @classmethod
    def validate_cors_allow_origins(cls, value: str | None) -> List[str]:
        if not value:
            return ["http://localhost:5173"]

        if isinstance(value, str):
            origins = [origin.strip() for origin in value.split(",") if origin.strip()]
            return origins if origins else ["http://localhost:5173"]
        return value if isinstance(value, list) else ["http://localhost:5173"]

    def get_deepseek_config(self) -> dict:
        return {
            "api_key": self.DEEPSEEK_API_KEY,
            "model": self.DEEPSEEK_MODEL,
            "base_url": self.DEEPSEEK_BASE_URL,
        }

    @classmethod
    def from_env(cls, env: str = None):
        env = env or os.getenv("ENV", "dev")
        env_file = f".env.{env.lower}"
        return cls(_env_file=env_file, _env_file_encoding="utf-8")


settings = Settings()
