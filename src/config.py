import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Config:
    max_item_hours: int = 72


def load_config() -> Config:
    """Load configuration from the .env file in the project root."""
    env_file = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=env_file, override=False)

    return Config(
        max_item_hours=int(os.environ.get("MAX_ITEM_HOURS", "").strip() or "72"),
    )


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Return a cached Config loaded on the first call."""
    return load_config()
