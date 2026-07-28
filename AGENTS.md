# AGENTS.md

## Project

AI Dev Digest Bot — Telegram-бот, который каждый день собирает новости из AI/dev
сферы, фильтрует шум и отправляет краткую сводку. Полное описание, установка и
список источников — в [README.md](README.md).

Фокус: Claude Code, OpenAI Codex/GPT tools, opencode, AI coding agents, MCP,
self-hosted AI tools, практическая автоматизация разработки.

---

## Stack

Python 3.12+, python-telegram-bot, APScheduler (asyncio), SQLite, Ollama
(gemma3:4b, с эвристическим fallback без LLM). Полный список пакетов —
`requirements.txt`.

---

## Main Flow

```text
DIGEST_TIME (APScheduler)
→ collect_all()   сбор из всех источников, фильтр по возрасту
→ score_news()    LLM-скоринг, эвристика при сбое Ollama
→ storage         дедуп внутри запуска и между запусками (sent_links)
→ build_digest()  сортировка по score, группировка по категориям
→ send_digest()   отправка в Telegram, запись в digest_runs
```

Тот же путь запускается вручную командой `/digest`; оба пути защищены
`asyncio.Lock` в `send_digest`, поэтому не пересекаются.

---

## Structure

```text
src/
  main.py         точка входа: БД, бот, планировщик
  config.py       конфиг из .env (Config, load_config, get_config)
  models.py       NewsItem dataclass
  collect.py      сбор из источников, фильтр по возрасту
  sources.py      описание источников (name, url, type, category)
  llm.py          LLM-скоринг через Ollama + эвристический fallback
  digest.py       форматирование дайджеста
  telegram.py     Telegram-бот, команды, send_digest
  scheduler.py    APScheduler, ежедневный job
  storage.py      SQLite: news_items, digest_runs, sent_links
data/             SQLite-файл, создаётся автоматически (см. Storage)
tests/            pytest, по одному файлу на модуль src/
```

---

## News Model

`NewsItem`: title, url, source, published_at, summary, score,
why_it_matters, action.

Примечание: поле `why_it_matters` по факту хранит русский summary от LLM
(prompt в `llm.py` запрашивает `summary`, не `why_it_matters`/`action`) —
имя поля не меняли, чтобы не трогать storage-схему без необходимости.

---

## Scoring

Score 0..5, в дайджест попадают только `score >= 3`.

Приоритет: coding agents, developer tools, workflow automation, практические
обновления, новые AI-инструменты.
Игнорировать: общий AI-хайп, маркетинг, crypto AI spam.

---

## Telegram Digest Format

Реальный формат из `src/digest.py` (`format_digest_message` + `build_digest`):

```text
*🤖 AI Dev Digest*
🔥 Main Updates

1. title
   summary
   Action: ...
   🔗 url

🧰 New Tools
...

---
```

Категории и заголовки — `CATEGORY_HEADERS`/`CATEGORY_ORDER` в `digest.py`,
привязаны к `source.category` из `sources.py`. Markdown экранируется
`_escape_markdown`; `action` выводится только если LLM его вернул.

---

## Commands

- `/digest` — собрать и отправить дайджест сейчас
- `/health` — проверить конфиг и БД
- `/sources` — список источников

---

## Rules

- Простая архитектура, без overengineering и преждевременных абстракций
- Async — основной стиль (`asyncio.Lock`, async-хендлеры, AsyncIOScheduler)
- Секреты только в `.env`, никогда не коммитить
- Одна ответственность на модуль
- Читаемый код важнее «умного»

---

## Storage

SQLite-таблицы: `news_items`, `digest_runs`, `sent_links`.
Дедуп — по MD5 хешу URL (`Storage._compute_hash`).
`Storage.__init__` сам создаёт родительскую директорию `db_path`, если её нет
(кроме `:memory:`) — вручную создавать `data/` не нужно.

---

## Environment

Обязательные переменные и переменные с дефолтами — таблица в README
(`.env.example` содержит актуальный набор ключей).

---

## Lint

Правила ruff зафиксированы в `pyproject.toml`: `E, F, I, UP`.
`BLE001` (flake8-blind-except) осознанно исключён — широкий
`except Exception` в collect.py/llm.py/scheduler.py/telegram.py изолирует
сбой одного источника/LLM/Telegram от остального пайплайна.

---

## MVP Goals

Выполнено: сбор RSS/API-источников, генерация и отправка дайджеста,
дедуп, ежедневный запуск по расписанию (см. `docs/TASKS.md` по milestones).

Не в скоупе: web UI, multi-user, vector DB, RAG, browser automation,
подписки, admin panel.
