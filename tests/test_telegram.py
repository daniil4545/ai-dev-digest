import asyncio
from unittest.mock import AsyncMock, MagicMock

from src.config import Config
from src.models import NewsItem
from src.sources import SOURCES
from src.telegram import (
    digest_handler,
    health_handler,
    send_digest,
    sources_handler,
    start_handler,
)


def _make_update_and_context():
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    update.effective_chat.id = 12345
    context = MagicMock()
    context.bot.send_message = AsyncMock()
    app = MagicMock()
    app.bot.send_message = AsyncMock()
    context.application = app
    return update, context


def _run(async_func, *args, **kwargs):
    return asyncio.run(async_func(*args, **kwargs))


def _fake_item(title="Test", score=3.0):
    return NewsItem(
        title=title,
        url="https://example.com",
        source="OpenAI Blog",
        published_at="2025-01-01T00:00:00",
        summary="",
        score=score,
        why_it_matters="Why",
        action="Read",
    )


def _mock_config(mocker):
    return mocker.patch(
        "src.telegram.get_config",
        return_value=Config(
            telegram_bot_token="test",
            telegram_chat_id="12345",
            ollama_model="gemma3:4b",
            ollama_host="http://localhost:11434",
            digest_time="08:30",
            timezone="Europe/Amsterdam",
        ),
    )


class TestStartCommand:
    def test_start_command(self) -> None:
        update, context = _make_update_and_context()
        _run(start_handler, update, context)
        update.message.reply_text.assert_awaited_once()
        text = update.message.reply_text.await_args[0][0]
        assert "AI Dev Digest Bot" in text
        assert "/digest" in text
        assert "/health" in text
        assert "/sources" in text


class TestHealthCommand:
    def test_health_command(self, mocker) -> None:
        mocker.patch(
            "src.telegram.get_config",
            return_value=Config(
                telegram_bot_token="test",
                telegram_chat_id="12345",
                ollama_model="gemma3:4b",
                ollama_host="http://localhost:11434",
                digest_time="08:30",
                timezone="Europe/Amsterdam",
            ),
        )
        update, context = _make_update_and_context()
        _run(health_handler, update, context)
        reply = update.message.reply_text.await_args[0][0]
        assert "System status" in reply
        assert "Config: OK" in reply
        assert "Database: OK" in reply
        assert f"{len(SOURCES)} configured" in reply

    def test_health_command_config_fails(self, mocker) -> None:
        mocker.patch("src.telegram.get_config", side_effect=ValueError("no token"))
        mocker.patch(
            "src.telegram.Storage",
            return_value=MagicMock(),
        )
        update, context = _make_update_and_context()
        _run(health_handler, update, context)
        reply = update.message.reply_text.await_args[0][0]
        assert "System status" in reply
        assert "Config: FAIL" in reply
        assert f"Sources: {len(SOURCES)} configured" in reply


class TestSourcesCommand:
    def test_sources_command(self) -> None:
        update, context = _make_update_and_context()
        _run(sources_handler, update, context)
        reply = update.message.reply_text.await_args[0][0]
        for source in SOURCES:
            assert source.name in reply
        assert str(len(SOURCES)) in reply


class TestDigestCommand:
    def test_digest_command_empty(self, mocker) -> None:
        _mock_config(mocker)
        mocker.patch("src.telegram.collect_all", return_value=[])
        mocker.patch("src.telegram.score_news", return_value=[])
        mocker.patch("src.telegram.Storage")
        update, context = _make_update_and_context()
        _run(digest_handler, update, context)
        update.message.reply_text.assert_awaited_with("⏳ Collecting news...")
        context.application.bot.send_message.assert_awaited_with(
            chat_id=12345,
            text="No news worth reporting today.",
        )

    def test_digest_command_success(self, mocker) -> None:
        _mock_config(mocker)
        items = [_fake_item(title="Claude update", score=4.0)]
        mocker.patch("src.telegram.collect_all", return_value=items)
        mocker.patch("src.telegram.score_news", return_value=items)
        mock_storage = mocker.patch("src.telegram.Storage")
        mock_storage.return_value.was_link_sent.return_value = False
        mock_format = mocker.patch(
            "src.telegram.format_digest_message",
            return_value="*Digest content*",
        )
        update, context = _make_update_and_context()
        _run(digest_handler, update, context)
        mock_format.assert_called_once_with(items)
        context.application.bot.send_message.assert_awaited_with(
            chat_id=12345,
            text="*Digest content*",
            parse_mode="Markdown",
        )


class TestSendDigest:
    def test_send_digest_collect_fails(self, mocker) -> None:
        _mock_config(mocker)
        mocker.patch(
            "src.telegram.collect_all", side_effect=RuntimeError("network down")
        )
        app = MagicMock()
        app.bot.send_message = AsyncMock()
        _run(send_digest, app, 12345)
        app.bot.send_message.assert_awaited_with(
            chat_id=12345,
            text="Failed to collect news",
        )

    def test_send_digest_score_fails(self, mocker) -> None:
        _mock_config(mocker)
        mocker.patch("src.telegram.collect_all", return_value=[_fake_item()])
        mocker.patch("src.telegram.score_news", side_effect=RuntimeError("ollama down"))
        app = MagicMock()
        app.bot.send_message = AsyncMock()
        _run(send_digest, app, 12345)
        app.bot.send_message.assert_awaited_with(
            chat_id=12345,
            text="Failed to score news",
        )

    def test_send_digest_empty(self, mocker) -> None:
        _mock_config(mocker)
        mocker.patch("src.telegram.collect_all", return_value=[])
        mocker.patch("src.telegram.score_news", return_value=[])
        mock_storage = mocker.patch("src.telegram.Storage")
        app = MagicMock()
        app.bot.send_message = AsyncMock()
        _run(send_digest, app, 12345)
        app.bot.send_message.assert_awaited_with(
            chat_id=12345,
            text="No news worth reporting today.",
        )
        mock_storage.return_value.save_run.assert_called_with(0, "empty")

    def test_send_digest_all_scores_below_threshold(self, mocker) -> None:
        _mock_config(mocker)
        items = [_fake_item(title="Low", score=1.0)]
        mocker.patch("src.telegram.collect_all", return_value=items)
        mocker.patch("src.telegram.score_news", return_value=[])
        mock_storage = mocker.patch("src.telegram.Storage")
        app = MagicMock()
        app.bot.send_message = AsyncMock()

        _run(send_digest, app, 12345)

        mock_storage.return_value.save_item.assert_called_once_with(items[0])
        mock_storage.return_value.save_run.assert_called_with(0, "empty")
        app.bot.send_message.assert_awaited_with(
            chat_id=12345,
            text="No news worth reporting today.",
        )

    def test_send_digest_success(self, mocker) -> None:
        _mock_config(mocker)
        items = [_fake_item(title="GPT-5", score=5.0)]
        mocker.patch("src.telegram.collect_all", return_value=items)
        mocker.patch("src.telegram.score_news", return_value=items)
        mock_storage = mocker.patch("src.telegram.Storage")
        mock_storage.return_value.was_link_sent.return_value = False
        mocker.patch(
            "src.telegram.format_digest_message",
            return_value="*Digest*",
        )
        app = MagicMock()
        app.bot.send_message = AsyncMock()
        _run(send_digest, app, 12345)
        app.bot.send_message.assert_awaited_with(
            chat_id=12345,
            text="*Digest*",
            parse_mode="Markdown",
        )
        mock_storage.return_value.mark_link_sent.assert_called_once_with(items[0].url)
        mock_storage.return_value.save_run.assert_called_with(1, "success")

    def test_send_digest_skips_already_sent_links(self, mocker) -> None:
        _mock_config(mocker)
        items = [_fake_item(title="Old", score=5.0)]
        mocker.patch("src.telegram.collect_all", return_value=items)
        mocker.patch("src.telegram.score_news", return_value=items)
        mock_storage = mocker.patch("src.telegram.Storage")
        mock_storage.return_value.was_link_sent.return_value = True
        app = MagicMock()
        app.bot.send_message = AsyncMock()

        _run(send_digest, app, 12345)

        app.bot.send_message.assert_awaited_with(
            chat_id=12345,
            text="No news worth reporting today.",
        )
        mock_storage.return_value.mark_link_sent.assert_not_called()

    def test_send_digest_deduplicates_current_batch(self, mocker) -> None:
        _mock_config(mocker)
        items = [
            _fake_item(title="First", score=5.0),
            _fake_item(title="Second", score=4.0),
        ]
        mocker.patch("src.telegram.collect_all", return_value=items)
        mocker.patch("src.telegram.score_news", return_value=items)
        mock_storage = mocker.patch("src.telegram.Storage")
        mock_storage.return_value.was_link_sent.return_value = False
        mock_format = mocker.patch(
            "src.telegram.format_digest_message",
            return_value="*Digest*",
        )
        app = MagicMock()
        app.bot.send_message = AsyncMock()

        _run(send_digest, app, 12345)

        mock_format.assert_called_once_with([items[0]])
