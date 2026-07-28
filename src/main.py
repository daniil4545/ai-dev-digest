import logging

from telegram.ext import Application

from src.config import get_config
from src.scheduler import setup_scheduler, start_scheduler
from src.telegram import run_polling, setup_application

logger = logging.getLogger(__name__)


async def post_init(app: Application) -> None:
    scheduler = setup_scheduler(app)
    start_scheduler(scheduler)

    config = get_config()
    logger.info(
        "Bot started. Daily digest at %s (%s)", config.digest_time, config.timezone
    )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    config = get_config()
    app = setup_application(post_init=post_init)

    logger.info(
        "Bot starting. Daily digest at %s (%s)", config.digest_time, config.timezone
    )
    run_polling(app)


if __name__ == "__main__":
    main()
