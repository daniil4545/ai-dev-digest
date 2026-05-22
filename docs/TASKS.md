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

- [~] **M2: Sources + Collect**
      `sources.py` — описание источников (name, url, type, parser).
      `collect.py` — сбор из RSS (feedparser), HN (API), Reddit (API), GitHub Trending (scrape),
      нормализация в `NewsItem` (dataclass).
      Проверка: запустить collect, проверить что вернулись `NewsItem` с заполненными полями.

- [ ] **M3: LLM Scoring**
      `llm.py` — Ollama client (gemma3:4b), функция `score_news(items)` → возвращает items с score/why_it_matters/action,
      фильтр `score >= 3`.
      Проверка: `pytest tests/test_llm.py` с mock ollama.

- [ ] **M4: Digest**
      `digest.py` — сортировка по score, группировка по темам, форматирование в Telegram-разметку.
      Проверка: `pytest tests/test_digest.py` — на вход набор NewsItem, на выход строка с ожидаемой структурой.

- [ ] **M5: Telegram Commands**
      `telegram.py` — `Application` из `python-telegram-bot`, команды `/digest` (запустить сбор и отправить),
      `/health` (проверка БД + API ключей), `/sources` (список источников).
      Проверка: запустить `python src/main.py`, отправить команды в Telegram.

- [ ] **M6: Scheduler + Main**
      `scheduler.py` — APScheduler, ежедневный job в `DIGEST_TIME`.
      `main.py` — инициализация БД, запуск bot polling + scheduler.
      Проверка: запустить, проверить что scheduler зарегистрирован и бот отвечает.

- [ ] **M7: Tests**
      Покрыть ключевые сценарии: пустые источники, дубликаты, ошибки API, все score < 3.
      Проверка: `pytest tests/ -v` — все зелёные.

- [ ] **M8: README**
      Установка, `.env`, запуск, пример дайджеста.
