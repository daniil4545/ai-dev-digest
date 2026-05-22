# Changelog

## [Unreleased]

### Added
- Project scaffold: src/, tests/, data/ directories, requirements.txt, .env.example
- Python venv with all dependencies including ruff
- .gitignore for venv and env files
- Git repository initialized
- `src/models.py` — NewsItem dataclass with 8 fields
- `src/config.py` — Config dataclass with env loading via python-dotenv and cached singleton
- `src/storage.py` — SQLite storage with news_items, digest_runs, sent_links tables
- `tests/test_storage.py` — 6 tests covering CRUD, duplicate detection, link tracking
- `src/sources.py` — 9 source configs (RSS, HN API, Reddit API, GitHub Trending)
- `src/collect.py` — 4 parsers with FETCH_MAP dispatcher and error handling
- `tests/test_collect.py` — 20 tests covering all parsers, error cases, and collect_all
- `src/llm.py` — LLM scoring via Ollama with heuristic fallback, batch and sequential modes
- `tests/test_llm.py` — 13 tests covering LLM, heuristic, batch, and error handling

### Changed
- LLM provider switched from OpenAI to Ollama (gemma3:4b) for news scoring

### Removed
- OpenAI and Anthropic API keys from env template
