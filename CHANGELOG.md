# Changelog

## [Unreleased]

### Added
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
- `score_news` / `score_news_batch` — two-pass scoring: heuristic first, LLM only for non-matching items
- LLM prompt always requests Russian summary (`summary` field) instead of English `why_it_matters` + `action`
- `_heuristic_score` — summary now comes from source data (`item.summary` or `item.title`)
- Digest format: `1. Title\n   Summary (150 chars)\n   🔗 url` (removed Markdown link syntax)
- Scheduler startup moved to `post_init` callback (fixes `RuntimeError: no running event loop`)

### Fixed
- JSON parsing for Ollama responses wrapped in ```json code blocks with trailing commas or single quotes
- `RuntimeError: no running event loop` on `AsyncIOScheduler.start()` (moved to async post_init)
- `test_collect_all` making real network requests (added `clear=True` to `mocker.patch.dict`)
- Hardcoded source count in tests replaced with dynamic `len(SOURCES)`
