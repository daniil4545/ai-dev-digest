import asyncio
from unittest.mock import AsyncMock, MagicMock

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
        mocker.patch("src.telegram.get_config", return_value=MagicMock())
        update, context = _make_update_and_context()
        _run(health_handler, update, context)
        reply = update.message.reply_text.await_args[0][0]
        assert "All systems operational" in reply
        assert "Config: OK" in reply
        assert "Database: OK" in reply
        assert "9 configured" in reply

    def test_health_command_config_fails(self, mocker) -> None:
        mocker.patch("src.telegram.get_config", side_effect=ValueError("no token"))
        update, context = _make_update_and_context()
        _run(health_handler, update, context)
        reply = update.message.reply_text.await_args[0][0]
        assert "All systems operational" in reply
        assert "Config: FAIL" in reply
        assert "Sources: 9 configured" in reply


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
        mocker.patch("src.telegram.collect_all", return_value=[])
        mocker.patch("src.telegram.score_news", return_value=[])
        update, context = _make_update_and_context()
        _run(digest_handler, update, context)
        update.message.reply_text.assert_awaited_with("⏳ Collecting news...")
        context.application.bot.send_message.assert_awaited_with(
            chat_id=12345,
            text="No news worth reporting today.",
        )

    def test_digest_command_success(self, mocker) -> None:
        items = [_fake_item(title="Claude update", score=4.0)]
        mocker.patch("src.telegram.collect_all", return_value=items)
        mocker.patch("src.telegram.score_news", return_value=items)
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
        mocker.patch("src.telegram.collect_all", side_effect=RuntimeError("network down"))
        app = MagicMock()
        app.bot.send_message = AsyncMock()
        _run(send_digest, app, 12345)
        app.bot.send_message.assert_awaited_with(
            chat_id=12345,
            text="Failed to collect news",
        )

    def test_send_digest_score_fails(self, mocker) -> None:
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
        mocker.patch("src.telegram.collect_all", return_value=[])
        mocker.patch("src.telegram.score_news", return_value=[])
        app = MagicMock()
        app.bot.send_message = AsyncMock()
        _run(send_digest, app, 12345)
        app.bot.send_message.assert_awaited_with(
            chat_id=12345,
            text="No news worth reporting today.",
        )

    def test_send_digest_success(self, mocker) -> None:
        items = [_fake_item(title="GPT-5", score=5.0)]
        mocker.patch("src.telegram.collect_all", return_value=items)
        mocker.patch("src.telegram.score_news", return_value=items)
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
