"""Application configuration using pydantic-settings."""

from pathlib import Path

from pydantic_settings import BaseSettings


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"


class Settings(BaseSettings):
    # Reddit API
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "gw2trading:v0.1.0"

    # GW2 API
    gw2_api_base_url: str = "https://api.guildwars2.com/v2"
    gw2_api_key: str = ""

    # Database
    db_path: Path = DATA_DIR / "gw2trading.db"

    # Polling intervals (seconds)
    price_poll_top20_interval: int = 900  # 15 minutes
    price_poll_top200_interval: int = 3600  # 1 hour
    reddit_poll_interval: int = 3600  # 1 hour
    wiki_poll_interval: int = 3600  # 1 hour

    model_config = {"env_file": BASE_DIR / ".env", "env_file_encoding": "utf-8"}


settings = Settings()
