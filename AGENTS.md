# AGENTS.md

## Project

ai-dev-digest собирает AI и dev-новости и готовит дайджест для владельца: он читает его и пишет посты в свой Telegram-канал. Сбор и дедуп делает Python, отбор и разбор - Claude Code через скилл `/digest`. Установка и источники - [README.md](README.md), спека - [docs/plans/claude-digest.md](docs/plans/claude-digest.md).

## Main Flow

```text
/digest (скилл .claude/skills/digest)
  python -m src.main collect   collect_all, нормализация url, окно MAX_ITEM_HOURS, минус sent_links
  отбор до 10 + «Коротко»      приоритеты в скилле
  WebFetch оригиналов          не открылся - пересказ из кандидатов, потом summary
  digests/YYYY-MM-DD.md        не перезаписывается, повтор в тот же день - -2, -3
  python -m src.main mark      ссылки файла в sent_links
```

## Structure

```text
src/
  main.py      CLI: collect_candidates, mark_digest
  collect.py   сбор из источников, normalize_url, фильтр по возрасту
  sources.py   SOURCES (name, url, type)
  storage.py   SQLite: sent_links
  config.py    Config из .env (MAX_ITEM_HOURS)
  models.py    NewsItem
tests/         pytest, по файлу на модуль src/
```

## News Model

`NewsItem`: title, url, source, published_at, summary, score. `score` - популярность в источнике (очки HN, звёзды GitHub), у RSS 0; решений по нему код не принимает. В JSON для скилла идут все поля.

## Storage

Одна таблица `sent_links(url UNIQUE)`: ссылка была в дайджесте. Пишет только `mark`, читает `collect`. `Storage.__init__` сам создаёт родительскую директорию БД. Таблицы `news_items` и `digest_runs` остались в старых БД от Telegram-бота, код их не использует.

## Rules

- Сетевые вызовы с таймаутом `REQUEST_TIMEOUT`; сбой одного источника не валит сбор
- Что уже показано, решает `mark` по ссылкам файла, а не модель
- Автотесты без сети: HTTP подменяется, SQLite настоящая (`:memory:` или `tmp_path`)
- Простая архитектура, одна ответственность на модуль

## Lint

Правила ruff в `pyproject.toml`: `E, F, I, UP`. `BLE001` осознанно исключён: широкий `except Exception` в `collect.py` изолирует сбой одного источника.

## Not in scope

Публикация куда-либо, расписание, web UI, multi-user.
