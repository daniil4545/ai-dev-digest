import logging

from src.config import get_config
from src.scheduler import setup_scheduler, start_scheduler
from src.telegram import setup_application, run_polling

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    config = get_config()
    app = setup_application()
    scheduler = setup_scheduler(app)
    start_scheduler(scheduler)

    logger.info("Bot started. Daily digest at %s (%s)", config.digest_time, config.timezone)
    run_polling(app)


if __name__ == "__main__":
    main()
