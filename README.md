# ai-dev-digest

Ежедневный Telegram-дайджест AI/dev-новостей из 13 источников: сбор, скоринг локальной LLM (Ollama), краткая сводка на русском в заданное время.

Пайплайн: RSS, Hacker News API, Reddit API и GitHub Trending собираются в общий список, фильтруются по возрасту, оцениваются LLM, сортируются по score и уходят одним сообщением в Telegram. Пайплайн переживает сбой любого источника и недоступность LLM.

## Быстрый старт

```bash
git clone https://github.com/daniil4545/ai-dev-digest.git
cd ai-dev-digest
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # заполнить TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID
python -m src.main
```

Режим отладки, результат за 1-2 минуты (по 1 новости с источника):

```bash
DEBUG_SCOOP=1 python -m src.main
```

## Инженерные решения

- **Изоляция сбоев источников.** Каждый источник опрашивается независимо; сетевой сбой или malformed payload логируется и не валит сбор остальных 12.
- **Эвристический fallback без LLM.** При недоступности Ollama скоринг деградирует до keyword-эвристики; дайджест выходит в любом случае.
- **Дедуп между запусками.** Отправленные ссылки фиксируются в SQLite-таблице `sent_links` (`INSERT OR IGNORE`); повторы фильтруются и внутри одного запуска, и между запусками.
- **Сериализация запусков.** Ручной `/digest` и запуск по расписанию не пересекаются: отправка защищена asyncio-lock.
- **Журнал запусков.** Каждый запуск пишется в `digest_runs` со статусом `success`, `empty` или `failed`; это основа команды `/health`.
- **Тесты без сети.** Полный путь collect, score, storage, Telegram проверяется на fake-реализациях и временной SQLite.

## Команды

- `/digest` собрать и отправить дайджест сейчас
- `/health` проверить конфиг и БД
- `/sources` список источников

## Настройка `.env`

| Переменная | Описание |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Токен бота от @BotFather |
| `TELEGRAM_CHAT_ID` | ID чата (узнать через @userinfobot) |
| `OLLAMA_MODEL` | Модель Ollama (по умолчанию gemma3:4b) |
| `OLLAMA_HOST` | Адрес Ollama (по умолчанию http://localhost:11434) |
| `DIGEST_TIME` | Время отправки дайджеста (по умолчанию 08:30) |
| `TIMEZONE` | Часовой пояс (по умолчанию Europe/Amsterdam) |
| `DEBUG_SCOOP` | `1` включает режим отладки |
| `MAX_ITEM_HOURS` | Максимальный возраст новости в часах (по умолчанию 24) |

## Структура

```
src/
  main.py         точка входа
  config.py       конфиг из .env
  models.py       NewsItem dataclass
  collect.py      сбор новостей из источников
  sources.py      описание источников
  llm.py          LLM-скоринг через Ollama и эвристический fallback
  digest.py       форматирование дайджеста
  telegram.py     Telegram-бот
  scheduler.py    ежедневный планировщик
  storage.py      SQLite: sent_links, digest_runs
tests/            pytest
```

## Источники

OpenAI Blog, Anthropic Blog, Cursor Blog, Google DeepMind, Groq News, Stability AI, Claude Code Changelog, OpenCode Releases, GitHub Trending, Hacker News, Reddit (r/ClaudeAI, r/OpenAI, r/LocalLLaMA).

## Тесты

```bash
ruff format --check .
ruff check .
pytest -q
```

## Стек

Python 3.12, python-telegram-bot, APScheduler, SQLite, Ollama.

## Лицензия

MIT, см. [LICENSE](LICENSE).
