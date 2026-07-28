import asyncio
import logging
from pathlib import Path

from telegram.ext import Application, CommandHandler, ContextTypes

from src.collect import collect_all
from src.config import get_config
from src.digest import format_digest_message
from src.llm import score_news
from src.models import NewsItem
from src.sources import SOURCES
from src.storage import Storage
from telegram import Update

logger = logging.getLogger(__name__)

_DB_PATH = str(Path(__file__).resolve().parent.parent / "data" / "digest.db")
_SEND_DIGEST_LOCK = asyncio.Lock()


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    await update.message.reply_text(
        "🤖 AI Dev Digest Bot\n\n"
        "Каждое утро собираю свежие новости из мира AI и разработки.\n"
        "Доступные команды:\n"
        "/digest — получить дайджест сейчас\n"
        "/health — проверить состояние\n"
        "/sources — список источников"
    )


async def health_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    config_ok = False
    db_ok = False
    try:
        get_config()
        config_ok = True
    except Exception as e:
        logger.warning("Health check config failed: %s", e)
    try:
        storage = Storage(_DB_PATH)
        storage.save_run(0, "health")
        storage.close()
        db_ok = True
    except Exception as e:
        logger.warning("Health check database failed: %s", e)

    if config_ok and db_ok:
        status = "✅"
    elif config_ok or db_ok:
        status = "⚠️"
    else:
        status = "❌"
    lines = [f"{status} System status"]
    lines.append(f"• Config: {'OK' if config_ok else 'FAIL'}")
    lines.append(f"• Database: {'OK' if db_ok else 'FAIL'}")
    lines.append(f"• Sources: {len(SOURCES)} configured")
    await update.message.reply_text("\n".join(lines))


async def sources_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return
    type_labels = {
        "rss": "RSS",
        "hn_api": "API",
        "reddit_api": "API",
        "github_trending": "Web",
    }
    lines = [f"📡 Sources ({len(SOURCES)})", ""]
    for source in SOURCES:
        label = type_labels.get(source.type, source.type)
        lines.append(f"• {source.name} ({label})")
    await update.message.reply_text("\n".join(lines))


async def send_digest(app: Application, chat_id: int) -> None:
    if _SEND_DIGEST_LOCK.locked():
        await app.bot.send_message(chat_id=chat_id, text="Digest is already running.")
        return

    async with _SEND_DIGEST_LOCK:
        await _send_digest(app, chat_id)


async def _send_digest(app: Application, chat_id: int) -> None:
    config = get_config()

    try:
        items = await asyncio.to_thread(
            collect_all,
            debug_scoop=config.debug_scoop,
            max_item_hours=config.max_item_hours,
        )
        logger.info("Collected %d items", len(items))
    except Exception as e:
        logger.error("Failed to collect news: %s", e)
        await app.bot.send_message(chat_id=chat_id, text="Failed to collect news")
        return

    try:
        scored = await asyncio.to_thread(score_news, items)
        logger.info("Scored %d items, %d passed filter", len(items), len(scored))
    except Exception as e:
        logger.error("Failed to score news: %s", e)
        await app.bot.send_message(chat_id=chat_id, text="Failed to score news")
        return

    storage = Storage(_DB_PATH)
    try:
        for item in items:
            storage.save_item(item)
    except Exception as e:
        logger.error("Failed to store results: %s", e)
    finally:
        storage.close()

    storage = Storage(_DB_PATH)
    try:
        seen: list[NewsItem] = []
        current_urls: set[str] = set()
        skipped = 0
        for item in scored:
            url_key = item.url.strip().lower()
            if url_key in current_urls or storage.was_link_sent(item.url):
                skipped += 1
            else:
                current_urls.add(url_key)
                seen.append(item)
        if skipped:
            logger.info("Dropped %d already-sent links", skipped)
        scored = seen
    except Exception as e:
        logger.error("Failed to check duplicates: %s", e)
    finally:
        storage.close()

    if not scored:
        storage = Storage(_DB_PATH)
        try:
            storage.save_run(0, "empty")
        except Exception as e:
            logger.error("Failed to record empty digest run: %s", e)
        finally:
            storage.close()
        await app.bot.send_message(
            chat_id=chat_id, text="No news worth reporting today."
        )
        return

    message = format_digest_message(scored)
    try:
        await app.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
    except Exception:
        storage = Storage(_DB_PATH)
        try:
            storage.save_run(len(scored), "failed")
        except Exception as e:
            logger.error("Failed to record failed digest run: %s", e)
        finally:
            storage.close()
        raise

    storage = Storage(_DB_PATH)
    try:
        for item in scored:
            storage.mark_link_sent(item.url)
        storage.save_run(len(scored), "success")
    except Exception as e:
        logger.error("Failed to mark sent links: %s", e)
    finally:
        storage.close()


async def digest_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.effective_chat is None:
        return
    chat_id = update.effective_chat.id
    await update.message.reply_text("⏳ Collecting news...")
    await send_digest(context.application, chat_id)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Unhandled error: %s", context.error)


def setup_application(post_init=None) -> Application:
    config = get_config()
    builder = Application.builder().token(config.telegram_bot_token)
    if post_init:
        builder = builder.post_init(post_init)
    app = builder.build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("digest", digest_handler))
    app.add_handler(CommandHandler("health", health_handler))
    app.add_handler(CommandHandler("sources", sources_handler))
    app.add_error_handler(error_handler)
    return app


def run_polling(app: Application) -> None:
    app.run_polling()
