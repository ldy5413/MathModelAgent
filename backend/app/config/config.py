from pydantic_settings import BaseSettings
from pathlib import Path
import os
from dotenv import load_dotenv


class Settings(BaseSettings):
    ENV: str
    DEEPSEEK_API_KEY: str
    DEEPSEEK_MODEL: str
    DEEPSEEK_BASE_URL: str
    MAX_CHAT_TURNS: int
    MAX_RETRIES: int
    E2B_API_KEY: str

    class Config:
        env_file = ".env.dev"
        env_file_encoding = "utf-8"

    def get_deepseek_config(self) -> dict:
        return {
            "api_key": self.DEEPSEEK_API_KEY,
            "model": self.DEEPSEEK_MODEL,
            "base_url": self.DEEPSEEK_BASE_URL,
        }


def load_env_config(env: str | None):
    env = env or os.getenv("ENV", "dev")
    env_file = f".env.{env}"

    if not Path(env_file).exists():
        raise FileNotFoundError(f"Environment file not found: {env_file}")

    load_dotenv(env_file)


load_env_config(os.getenv("ENV"))
settings = Settings()
