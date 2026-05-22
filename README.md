# AI Dev Digest Bot

Telegram-бот, который ежедневно в 08:30 собирает новости из AI/dev-сферы, фильтрует шум через локальную LLM (Ollama) и отправляет краткую сводку.

## Stack

Python 3.12+ · python-telegram-bot · APScheduler · SQLite · Ollama (gemma3:4b)

## Установка

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Настройка `.env`

| Переменная | Описание |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Токен бота от @BotFather |
| `TELEGRAM_CHAT_ID` | ID чата (узнать через @userinfobot) |
| `OLLAMA_MODEL` | Модель Ollama (по умолчанию gemma3:4b) |
| `OLLAMA_HOST` | Адрес Ollama (по умолч. http://localhost:11434) |
| `DIGEST_TIME` | Время отправки дайджеста (по умолч. 08:30) |
| `TIMEZONE` | Часовой пояс (по умолч. Europe/Amsterdam) |
| `DEBUG_SCOOP` | `1` — режим отладки (1 новость на источник) |
| `MAX_ITEM_HOURS` | Макс. возраст новости в часах (по умолч. 24) |

## Запуск

```bash
python -m src.main
```

## Команды

- `/digest` — собрать и отправить дайджест сейчас
- `/health` — проверить конфиг и БД
- `/sources` — список источников

## Режим отладки

```bash
DEBUG_SCOOP=1 python -m src.main
```

Берёт по 1 новости из каждого источника и показывает результат за 1-2 минуты.

## Как это работает

1. **Сбор** — RSS, Hacker News API, Reddit API, GitHub Trending (13 источников)
2. **Фильтр** — только новости за последние 24 часа
3. **Скоринг** — LLM (Ollama) оценивает новости, эвристика по keywords работает как fallback
4. **Дайджест** — сортировка по score, группировка по темам, саммари/action на русском
5. **Отправка** — Telegram-сообщение с Markdown escaping и защитой от повторных ссылок

## Надёжность pipeline

- Один битый источник или malformed payload не должен валить весь сбор.
- Повторные ссылки фильтруются внутри текущего запуска и между запусками через SQLite `sent_links`.
- Параллельные запуски `/digest` и scheduler сериализуются lock'ом.
- `digest_runs` фиксирует результат запуска: `success`, `empty` или `failed`.
- Тесты используют fake collect / fake LLM / fake Telegram, без реальных сетевых запросов.

## Структура

```
src/
  main.py         — точка входа
  config.py       — конфиг из .env
  models.py       — NewsItem dataclass
  collect.py      — сбор новостей из источников
  sources.py      — описание источников
  llm.py          — LLM скоринг через Ollama
  digest.py       — форматирование дайджеста
  telegram.py     — Telegram бот
  scheduler.py    — ежедневный планировщик
  storage.py      — SQLite хранилище
data/             — БД
tests/            — тесты (pytest)
```

## Источники

OpenAI Blog, Anthropic Blog, Cursor Blog, Google DeepMind, Groq News, Stability AI, Claude Code Changelog, OpenCode Releases, GitHub Trending, Hacker News, Reddit (r/ClaudeAI, r/OpenAI, r/LocalLLaMA).

## Тесты

```bash
ruff format --check .
ruff check .
pytest -q
```

Текущий smoke-набор проверяет полный путь collect → score → storage → Telegram на временной SQLite.
