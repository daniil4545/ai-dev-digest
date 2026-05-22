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

### Changed
- LLM provider switched from OpenAI to Ollama (gemma3:4b) for news scoring

### Removed
- OpenAI and Anthropic API keys from env template
