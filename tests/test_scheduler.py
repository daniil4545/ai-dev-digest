import asyncio
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

from src.scheduler import send_digest_job, setup_scheduler, start_scheduler


def _run(async_func, *args, **kwargs):
    return asyncio.run(async_func(*args, **kwargs))


class TestSetupScheduler:
    def test_setup_scheduler_creates_job(self, mocker) -> None:
        mock_config = MagicMock(
            digest_time="08:30",
            timezone="Europe/Amsterdam",
            telegram_chat_id="12345",
        )
        mocker.patch("src.scheduler.get_config", return_value=mock_config)

        scheduler_cls = mocker.patch("src.scheduler.AsyncIOScheduler", autospec=True)
        scheduler_instance = scheduler_cls.return_value
        app = MagicMock()

        result = setup_scheduler(app)

        assert result is scheduler_instance
        scheduler_instance.add_job.assert_called_once()
        pos_args, kwargs = scheduler_instance.add_job.call_args
        assert pos_args[1] == "cron"
        assert kwargs["hour"] == 8
        assert kwargs["minute"] == 30
        assert kwargs["timezone"] == ZoneInfo("Europe/Amsterdam")
        assert kwargs["args"] == [app, 12345]


class TestSendDigestJob:
    def test_calls_send_digest(self, mocker) -> None:
        mock_send_digest = mocker.patch(
            "src.scheduler.send_digest", new_callable=AsyncMock
        )
        app = MagicMock()
        _run(send_digest_job, app, 12345)
        mock_send_digest.assert_awaited_once_with(app, 12345)

    def test_logs_error_on_failure(self, mocker) -> None:
        mock_send_digest = mocker.patch(
            "src.scheduler.send_digest",
            new_callable=AsyncMock,
            side_effect=RuntimeError("fail"),
        )
        mock_logger = mocker.patch("src.scheduler.logger")
        app = MagicMock()
        _run(send_digest_job, app, 12345)
        mock_send_digest.assert_awaited_once_with(app, 12345)
        mock_logger.error.assert_called_once()
        assert mock_logger.error.call_args[0][1] is mock_send_digest.side_effect


class TestStartScheduler:
    def test_start_scheduler_starts(self, mocker) -> None:
        mock_config = MagicMock(digest_time="08:30", timezone="Europe/Amsterdam")
        mocker.patch("src.scheduler.get_config", return_value=mock_config)
        mock_logger = mocker.patch("src.scheduler.logger")
        scheduler = MagicMock()

        start_scheduler(scheduler)

        scheduler.start.assert_called_once()
        mock_logger.info.assert_called_once()
