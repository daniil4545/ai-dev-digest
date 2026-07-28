import pytest

from src.config import get_config, load_config


def _set_required_env(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")


class TestLoadConfig:
    def test_missing_bot_token_raises(self, monkeypatch) -> None:
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
        with pytest.raises(ValueError):
            load_config()

    def test_missing_chat_id_raises(self, monkeypatch) -> None:
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
        with pytest.raises(ValueError):
            load_config()

    def test_optional_defaults_applied(self, monkeypatch) -> None:
        _set_required_env(monkeypatch)
        for key in (
            "OLLAMA_MODEL",
            "OLLAMA_HOST",
            "DIGEST_TIME",
            "TIMEZONE",
            "DEBUG_SCOOP",
            "MAX_ITEM_HOURS",
        ):
            monkeypatch.delenv(key, raising=False)

        config = load_config()

        assert config.ollama_model == "gemma3:4b"
        assert config.ollama_host == "http://localhost:11434"
        assert config.digest_time == "08:30"
        assert config.timezone == "Europe/Amsterdam"
        assert config.debug_scoop is False
        assert config.max_item_hours == 24

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("1", True),
            ("true", True),
            ("yes", True),
            ("0", False),
            ("false", False),
            ("no", False),
        ],
    )
    def test_debug_scoop_parsing(self, monkeypatch, value, expected) -> None:
        _set_required_env(monkeypatch)
        monkeypatch.setenv("DEBUG_SCOOP", value)

        config = load_config()

        assert config.debug_scoop is expected


class TestGetConfig:
    def test_returns_cached_instance(self, monkeypatch) -> None:
        get_config.cache_clear()
        _set_required_env(monkeypatch)
        try:
            first = get_config()
            second = get_config()
            assert first is second
        finally:
            get_config.cache_clear()
