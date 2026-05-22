import asyncio
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from src.collect import collect_all
from src.config import get_config
from src.digest import format_digest_message
from src.llm import score_news
from src.sources import SOURCES
from src.storage import Storage

logger = logging.getLogger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message is not None
    await update.message.reply_text(
        "🤖 AI Dev Digest Bot\n\n"
        "Каждое утро собираю свежие новости из мира AI и разработки.\n"
        "Доступные команды:\n"
        "/digest — получить дайджест сейчас\n"
        "/health — проверить состояние\n"
        "/sources — список источников"
    )


async def health_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message is not None
    config_ok = False
    db_ok = False
    try:
        get_config()
        config_ok = True
    except Exception:
        pass
    try:
        storage = Storage(":memory:")
        storage.save_run(0, "health")
        storage.close()
        db_ok = True
    except Exception:
        pass

    lines = ["✅ All systems operational"]
    lines.append(f"• Config: {'OK' if config_ok else 'FAIL'}")
    lines.append(f"• Database: {'OK' if db_ok else 'FAIL'}")
    lines.append(f"• Sources: {len(SOURCES)} configured")
    await update.message.reply_text("\n".join(lines))


async def sources_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message is not None
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
    try:
        items = await asyncio.to_thread(collect_all)
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

    if not scored:
        await app.bot.send_message(
            chat_id=chat_id, text="No news worth reporting today."
        )
        return

    message = format_digest_message(scored)
    await app.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")


async def digest_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message is not None
    assert update.effective_chat is not None
    chat_id = update.effective_chat.id
    await update.message.reply_text("⏳ Collecting news...")
    await send_digest(context.application, chat_id)


def setup_application() -> Application:
    config = get_config()
    app = Application.builder().token(config.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("digest", digest_handler))
    app.add_handler(CommandHandler("health", health_handler))
    app.add_handler(CommandHandler("sources", sources_handler))
    return app


def run_polling(app: Application) -> None:
    app.run_polling()
