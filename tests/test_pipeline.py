import asyncio
import threading
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.config import Config
from src.models import NewsItem
from src.scheduler import send_digest_job
from src.storage import Storage
from src.telegram import send_digest


def _run(async_func, *args, **kwargs):
    return asyncio.run(async_func(*args, **kwargs))


def _config() -> Config:
    return Config(
        telegram_bot_token="test",
        telegram_chat_id="12345",
        ollama_model="gemma3:4b",
        ollama_host="http://localhost:11434",
        digest_time="08:30",
        timezone="Europe/Amsterdam",
    )


def _item(title: str, url: str, score: float = 4.0) -> NewsItem:
    return NewsItem(
        title=title,
        url=url,
        source="Fake Source",
        published_at="2025-01-01T00:00:00+00:00",
        summary="Summary",
        score=score,
        why_it_matters="Useful for AI dev workflows",
        action="Try it",
    )


def _fake_app() -> MagicMock:
    app = MagicMock()
    app.bot.send_message = AsyncMock()
    return app


@pytest.fixture
def pipeline_db(tmp_path, mocker) -> Path:
    db_path = tmp_path / "digest.db"
    mocker.patch("src.telegram._DB_PATH", str(db_path))
    return db_path


def test_smoke_e2e_fake_collect_llm_telegram(pipeline_db, mocker) -> None:
    items = [
        _item("Codex update", "https://example.com/codex", score=5.0),
        _item("Claude Code release", "https://example.com/claude", score=4.0),
    ]
    mocker.patch("src.telegram.get_config", return_value=_config())
    mocker.patch("src.telegram.collect_all", return_value=items)
    mocker.patch("src.telegram.score_news", return_value=items)

    app = _fake_app()
    _run(send_digest, app, 12345)

    sent = app.bot.send_message.await_args.kwargs
    assert sent["chat_id"] == 12345
    assert "Codex update" in sent["text"]
    assert sent["parse_mode"] == "Markdown"

    storage = Storage(str(pipeline_db))
    try:
        assert storage.was_link_sent("https://example.com/codex")
        runs = storage._conn.execute(
            "SELECT item_count, status FROM digest_runs"
        ).fetchall()
        assert [(r["item_count"], r["status"]) for r in runs] == [(2, "success")]
    finally:
        storage.close()


def test_pipeline_deduplicates_within_run_and_between_runs(pipeline_db, mocker) -> None:
    duplicate_a = _item("First title", "https://example.com/dup", score=5.0)
    duplicate_b = _item("Second title", "https://example.com/dup", score=4.0)
    fresh = _item("Fresh title", "https://example.com/fresh", score=4.0)

    mocker.patch("src.telegram.get_config", return_value=_config())
    mocker.patch(
        "src.telegram.collect_all", return_value=[duplicate_a, duplicate_b, fresh]
    )
    mocker.patch(
        "src.telegram.score_news", return_value=[duplicate_a, duplicate_b, fresh]
    )

    first_app = _fake_app()
    _run(send_digest, first_app, 12345)

    first_text = first_app.bot.send_message.await_args.kwargs["text"]
    assert "First title" in first_text
    assert "Second title" not in first_text
    assert "Fresh title" in first_text

    second_app = _fake_app()
    _run(send_digest, second_app, 12345)

    second_app.bot.send_message.assert_awaited_with(
        chat_id=12345,
        text="No news worth reporting today.",
    )

    storage = Storage(str(pipeline_db))
    try:
        runs = storage._conn.execute(
            "SELECT item_count, status FROM digest_runs ORDER BY id"
        ).fetchall()
        assert [(r["item_count"], r["status"]) for r in runs] == [
            (2, "success"),
            (0, "empty"),
        ]
    finally:
        storage.close()


def test_pipeline_records_failed_run_when_telegram_send_fails(
    pipeline_db, mocker
) -> None:
    item = _item("Codex update", "https://example.com/codex", score=5.0)
    mocker.patch("src.telegram.get_config", return_value=_config())
    mocker.patch("src.telegram.collect_all", return_value=[item])
    mocker.patch("src.telegram.score_news", return_value=[item])

    app = _fake_app()
    app.bot.send_message.side_effect = RuntimeError("telegram down")

    with pytest.raises(RuntimeError, match="telegram down"):
        _run(send_digest, app, 12345)

    storage = Storage(str(pipeline_db))
    try:
        assert not storage.was_link_sent(item.url)
        runs = storage._conn.execute(
            "SELECT item_count, status FROM digest_runs"
        ).fetchall()
        assert [(r["item_count"], r["status"]) for r in runs] == [(1, "failed")]
    finally:
        storage.close()


def test_parallel_digest_and_scheduler_are_serialized(pipeline_db, mocker) -> None:
    item = _item("Codex update", "https://example.com/codex", score=5.0)
    started = threading.Event()
    release = threading.Event()

    def blocking_collect(**_kwargs):
        started.set()
        release.wait()
        return [item]

    async def scenario() -> None:
        mocker.patch("src.telegram.get_config", return_value=_config())
        mocker.patch("src.telegram.collect_all", side_effect=blocking_collect)
        mocker.patch("src.telegram.score_news", return_value=[item])

        app = _fake_app()
        digest_task = asyncio.create_task(send_digest(app, 12345))
        assert await asyncio.to_thread(started.wait, 1)

        await send_digest_job(app, 12345)

        app.bot.send_message.assert_awaited_with(
            chat_id=12345,
            text="Digest is already running.",
        )

        release.set()
        await digest_task

        messages = [
            call.kwargs["text"] for call in app.bot.send_message.await_args_list
        ]
        assert messages.count("Digest is already running.") == 1
        assert any("Codex update" in message for message in messages)

    asyncio.run(scenario())
