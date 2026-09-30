# ai-dev-digest

[![CI](https://github.com/daniil4545/ai-dev-digest/actions/workflows/ci.yml/badge.svg)](https://github.com/daniil4545/ai-dev-digest/actions/workflows/ci.yml)

Дайджест AI и dev-новостей из 16 источников: Python собирает свежие новости и убирает уже показанные, Claude Code отбирает до 10 главных, читает оригиналы и пишет разбор на русском в markdown-файл.

Поток: `/digest` в сессии Claude Code, `collect` (кандидаты в JSON), отбор, чтение оригиналов, файл `digests/YYYY-MM-DD.md`, `mark` (ссылки файла больше не попадут в кандидаты).

## Быстрый старт

```bash
git clone https://github.com/daniil4545/ai-dev-digest.git
cd ai-dev-digest
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
claude            # в сессии: /digest
```

Без Claude Code сборщик работает как CLI:

```bash
python -m src.main collect                      # кандидаты в JSON в stdout, логи в stderr
python -m src.main mark digests/2026-09-30.md   # отметить ссылки дайджеста
```

## Инженерные решения

- **Изоляция сбоев источников.** Каждый источник опрашивается независимо; сетевой сбой или битая лента логируется и не валит сбор остальных.
- **Дедуп между запусками.** Ссылки из записанного дайджеста фиксируются в SQLite-таблице `sent_links` (`INSERT OR IGNORE`). Новость, которую не выбрали, может попасть в следующий дайджест, пока моложе окна.
- **Нормализация ссылок.** Без `utm_*` и хвостового `/`: одна статья из блога и с HN - один кандидат.
- **Решения в коде, текст у модели.** Что уже показано, решает детерминированный `mark` по ссылкам файла, а не модель.
- **Тесты без сети.** Сбор, дедуп и CLI проверяются на фейковых ответах и временной SQLite.

## Настройка `.env`

| Переменная | Описание |
|---|---|
| `MAX_ITEM_HOURS` | Окно свежести новостей в часах (по умолчанию 72) |

## Структура

```
.claude/skills/digest/  скилл /digest: отбор, разбор, формат файла
src/
  main.py       CLI: collect, mark
  collect.py    сбор, нормализация ссылок, фильтр по возрасту
  sources.py    список источников
  storage.py    SQLite: sent_links
  config.py     конфиг из .env
  models.py     NewsItem
tests/          pytest
digests/        дайджесты, в git не попадают
```

## Источники

OpenAI, Anthropic, Anthropic Engineering, Cursor, Google DeepMind, Google AI, Hugging Face, Simon Willison, Latent Space, Andrej Karpathy (два блога и YouTube), Habr (хаб AI), Reddit (r/ClaudeAI, r/OpenAI, r/LocalLLaMA одной лентой), Hacker News, GitHub Trending. Проверка каждой ленты - [docs/plans/claude-digest-sources.md](docs/plans/claude-digest-sources.md).

## Тесты

```bash
ruff format --check .
ruff check .
pytest -q
```

## Стек

Python 3.12, requests, feedparser, BeautifulSoup, SQLite, Claude Code.

## Лицензия

MIT, см. [LICENSE](LICENSE).
