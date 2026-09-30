import pytest

from src.config import load_config


@pytest.fixture(autouse=True)
def no_dotenv(monkeypatch):
    """Keep the developer's real .env out of the tests."""
    monkeypatch.setattr("src.config.load_dotenv", lambda **kwargs: None)


class TestLoadConfig:
    def test_default_window_is_72_hours(self, monkeypatch) -> None:
        monkeypatch.delenv("MAX_ITEM_HOURS", raising=False)

        assert load_config().max_item_hours == 72

    def test_window_from_env(self, monkeypatch) -> None:
        monkeypatch.setenv("MAX_ITEM_HOURS", "24")

        assert load_config().max_item_hours == 24
