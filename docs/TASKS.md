# TASKS.md

## Milestones

Одна сессия = один milestone. Каждый milestone начинается с TDD-контракта: определяем, что и как тестировать, затем реализация.

- [x] **M0: Scaffold**
      Создать `src/`, `data/`, `tests/`, `requirements.txt`, `.env.example`, `__init__.py`.
      Проверка: `python -c "import sys; sys.path.insert(0, 'src'); print('ok')"`

- [x] **M1: Config + Storage**
      `config.py` — загрузка всех переменных из `.env`.
      `storage.py` — SQLite: инициализация, таблицы `news_items`, `digest_runs`, `sent_links`,
      методы `save_item`, `is_duplicate`, `save_run`, `was_link_sent`, `get_recent_items`.
      Проверка: `pytest tests/test_storage.py` с `:memory:` SQLite.

- [x] **M2: Sources + Collect**
      `sources.py` — описание источников (name, url, type, parser).
      `collect.py` — сбор из RSS (feedparser), HN (API), Reddit (API), GitHub Trending (scrape),
      нормализация в `NewsItem` (dataclass).
      Проверка: запустить collect, проверить что вернулись `NewsItem` с заполненными полями.

- [x] **M3: LLM Scoring**
      `llm.py` — Ollama client (gemma3:4b), функция `score_news(items)` → возвращает items с score/why_it_matters/action,
      фильтр `score >= 3`.
      Проверка: `pytest tests/test_llm.py` с mock ollama.

- [x] **M4: Digest**
      `digest.py` — сортировка по score, группировка по темам, форматирование в Telegram-разметку.
      Проверка: `pytest tests/test_digest.py` — на вход набор NewsItem, на выход строка с ожидаемой структурой.

- [x] **M5: Telegram Commands**
      `telegram.py` — `Application` из `python-telegram-bot`, команды `/digest` (запустить сбор и отправить),
      `/health` (проверка БД + API ключей), `/sources` (список источников).
      Проверка: запустить `python src/main.py`, отправить команды в Telegram.

- [x] **M6: Scheduler + Main**
      `scheduler.py` — APScheduler, ежедневный job в `DIGEST_TIME`.
      `main.py` — инициализация БД, запуск bot polling + scheduler.
      Проверка: запустить, проверить что scheduler зарегистрирован и бот отвечает.

- [x] **M7: Stabilize Pipeline Tests**
      Зафиксировать рабочий скелет end-to-end: collect → score → storage → Telegram.
      Покрыть ключевые сценарии:
      - пустые sources;
      - частично битые внешние API payloads;
      - дубликаты внутри одного запуска и между запусками;
      - все score < 3;
      - Telegram send failure;
      - параллельный `/digest` + scheduler.
      Добавить smoke e2e с fake collect / fake LLM / fake Telegram без реальных сетевых запросов.
      Проверка: `ruff check .` и `pytest -q` — зелёные.

- [-] **M8-M10** (качество LLM-скоринга, формат Telegram, runbook) отменены: Telegram-бот и Ollama-скоринг удалены, дайджест пишет Claude Code.

- [x] **M11: Дайджест через Claude Code**
      Спека: [plans/claude-digest.md](plans/claude-digest.md), источники: [plans/claude-digest-sources.md](plans/claude-digest-sources.md).
      Этап 1 (сборщик и CLI `collect`/`mark`, удаление бота) и этап 2 (скилл `/digest`, документы) сделаны; первый дайджест 30.09.
      Проверка: `pytest -q`, `ruff check .`, `ruff format --check .`; прогон `/digest` и повторный прогон без повторов.
