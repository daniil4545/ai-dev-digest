# Changelog

## [Unreleased]

### Changed
- Дайджест пишет Claude Code: скилл `/digest` отбирает до 10 новостей, читает оригиналы и пишет разбор в `digests/YYYY-MM-DD.md`
- `src/main.py` - CLI `collect` (кандидаты в JSON без показанных ссылок) и `mark` (ссылки дайджеста в `sent_links`)
- Источники: добавлены Habr, Google AI, официальная лента DeepMind, Hugging Face, Anthropic Engineering, Simon Willison, Latent Space, Andrej Karpathy; Reddit одной RSS-лентой; убраны Groq, Stability, релизы Claude Code и OpenCode
- Ссылки нормализуются (без `utm_*` и хвостового `/`), дата Atom берётся из `updated`, summary без HTML, заголовки GitHub Trending без переводов строк
- `MAX_ITEM_HOURS` по умолчанию 72

### Removed
- Telegram-бот, APScheduler, Ollama-скоринг, форматтер Telegram, `DEBUG_SCOOP`, таблицы `news_items` и `digest_runs` в новых БД

### Added
- Pipeline smoke/e2e tests with fake collect, fake LLM, fake Telegram and temp SQLite
- Edge-case tests for empty sources, malformed HN/Reddit payloads, duplicate links, empty scoring results, Telegram send failures and concurrent digest runs
- `Storage.mark_link_sent()` helper for sent-link persistence
- `MAX_ITEMS_PER_SOURCE` limit (50) to prevent massive single-source collection
- `_filter_recent(items, hours)` — filters items older than N hours before scoring
- `debug_scoop` mode — collects 1 item per source when `DEBUG_SCOOP=1` (fast testing)
- `_extract_json` with multi-strategy parsing (code fences, curly-brace, trailing commas, single quotes)
- `_clean_json_string` — sanitizes trailing commas, Python booleans, single quotes in JSON
- `_shorten(text, max_chars=150)` — truncates summaries to 1-2 sentences
- `_clean_title` — strips newlines and extra whitespace from titles
- Duplicate link filtering in `send_digest` via `storage.was_link_sent`
- `httpx` logger set to WARNING to suppress Telegram polling spam
- Config options: `DEBUG_SCOOP`, `MAX_ITEM_HOURS`

### Changed
- `score_news` / `score_news_batch` — LLM is the primary scorer; heuristic scoring is used as fallback on LLM failures
- LLM prompt always requests Russian summary (`summary` field) instead of English `why_it_matters` + `action`
- `_heuristic_score` — summary now comes from source data (`item.summary` or `item.title`)
- Digest format: `1. Title\n   Summary\n   Action\n   🔗 url` with safe Markdown escaping
- `.env` loading no longer overrides already exported environment variables
- Duplicate detection now uses normalized URLs rather than title + URL hashes
- Scheduler startup moved to `post_init` callback (fixes `RuntimeError: no running event loop`)

### Fixed
- Telegram digest runs now record `success`, `empty` and `failed` after the actual send outcome
- Duplicate links are filtered both within the current digest batch and across previous sent links
- Concurrent manual/scheduled digest runs are serialized with an async lock
- Ollama calls now use a request timeout and LLM scores are clamped to the 0..5 range
- Malformed HN/Reddit payloads no longer abort the whole source collection
- `Storage.save_item()` now returns the existing row id for duplicate inserts
- JSON parsing for Ollama responses wrapped in ```json code blocks with trailing commas or single quotes
- `RuntimeError: no running event loop` on `AsyncIOScheduler.start()` (moved to async post_init)
- `test_collect_all` making real network requests (added `clear=True` to `mocker.patch.dict`)
- Hardcoded source count in tests replaced with dynamic `len(SOURCES)`
