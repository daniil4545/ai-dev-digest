import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Config:
    telegram_bot_token: str
    telegram_chat_id: str
    ollama_model: str = "gemma3:4b"
    ollama_host: str = "http://localhost:11434"
    digest_time: str = "08:30"
    timezone: str = "Europe/Amsterdam"
    debug_scoop: bool = False
    max_item_hours: int = 24


def _get_env(key: str, default: str | None = None) -> str:
    """Read an environment variable, raising if it is missing and has no default.

    Args:
        key: environment variable name.
        default: fallback value when the variable is not set or empty.

    Returns:
        the variable value.

    Raises:
        ValueError: the variable is required (no default) but not set.
    """
    value = os.environ.get(key, "").strip()
    if not value and default is None:
        raise ValueError(f"{key} is required but was empty or not set")
    return value if value else default  # type: ignore[return-value]


def load_config() -> Config:
    """Load configuration from .env file and return a Config dataclass.

    Searches for .env in the project root (parent of src/) and loads it.
    Raises ValueError if required variables are missing or empty.

    Returns:
        Config: populated configuration object.
    """
    env_file = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=env_file, override=False)

    return Config(
        telegram_bot_token=_get_env("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=_get_env("TELEGRAM_CHAT_ID"),
        ollama_model=_get_env("OLLAMA_MODEL", "gemma3:4b"),
        ollama_host=_get_env("OLLAMA_HOST", "http://localhost:11434"),
        digest_time=_get_env("DIGEST_TIME", "08:30"),
        timezone=_get_env("TIMEZONE", "Europe/Amsterdam"),
        debug_scoop=_get_env("DEBUG_SCOOP", "0") in ("1", "true", "yes"),
        max_item_hours=int(_get_env("MAX_ITEM_HOURS", "24")),
    )


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Return a cached singleton Config object.

    The first call loads configuration from .env; subsequent calls
    return the same cached instance.

    Returns:
        Config: cached configuration object.
    """
    return load_config()
