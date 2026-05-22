import logging
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application

from src.config import get_config
from src.telegram import send_digest

logger = logging.getLogger(__name__)


def setup_scheduler(app: Application) -> AsyncIOScheduler:
    config = get_config()
    hour, minute = map(int, config.digest_time.split(":"))
    tz = ZoneInfo(config.timezone)
    try:
        chat_id = int(config.telegram_chat_id)
    except (ValueError, TypeError) as e:
        raise ValueError(
            f"Invalid TELEGRAM_CHAT_ID: {config.telegram_chat_id!r}. "
            "Must be a numeric string."
        ) from e

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        send_digest_job,
        "cron",
        hour=hour,
        minute=minute,
        timezone=tz,
        args=[app, chat_id],
    )
    return scheduler


async def send_digest_job(app: Application, chat_id: int) -> None:
    try:
        await send_digest(app, chat_id)
        logger.info("Digest sent successfully")
    except Exception as e:
        logger.error("Failed to send digest: %s", e)


def start_scheduler(scheduler: AsyncIOScheduler) -> None:
    config = get_config()
    scheduler.start()
    logger.info(
        "Scheduled daily digest at %s (%s)", config.digest_time, config.timezone
    )
