# AGENTS.md

## Project

AI Dev Digest Bot — Telegram бот, который каждый день в 08:30 собирает новости из AI/dev сферы, фильтрует шум и отправляет краткую сводку.

Фокус:
- Claude Code
- OpenAI Codex / GPT tools
- opencode
- AI coding agents
- MCP
- self-hosted AI tools
- практическая автоматизация разработки

---

## Stack

- Python 3.12+
- python-telegram-bot
- APScheduler
- SQLite
- requests
- feedparser
- BeautifulSoup4
- python-dotenv
- pytest

LLM:
- OpenAI API
- Anthropic API
- Ollama (optional)

---

## Main Flow

```text
08:30 scheduler
→ collect news
→ normalize items
→ remove duplicates
→ score via LLM
→ build digest
→ send Telegram message
```

---

## Structure

```text
src/
  main.py
  config.py
  scheduler.py
  telegram.py
  collect.py
  digest.py
  llm.py
  storage.py
  sources.py

data/
tests/
```

---

## Sources

Initial sources:
- OpenAI blog
- Anthropic blog
- Claude Code changelog
- opencode releases
- GitHub Trending
- Hacker News
- Reddit:
  - r/ClaudeAI
  - r/OpenAI
  - r/LocalLLaMA

---

## News Model

Each item should contain:
- title
- url
- source
- published_at
- summary
- score
- why_it_matters
- action

---

## Scoring

Score news from 0 to 5.

Include only:
```text
score >= 3
```

Prioritize:
- coding agents
- developer tools
- workflow automation
- practical updates
- new AI tooling

Ignore:
- generic AI hype
- marketing news
- crypto AI spam

---

## Telegram Digest Format

```text
🤖 AI Dev Digest

🔥 Main Updates
- title
- why it matters
- action
- link

🧰 New Tools
...

📌 Try Today
...
```

---

## Commands

MVP:
- /digest
- /health
- /sources

---

## Rules

- Keep architecture simple
- No async for MVP
- No overengineering
- Use `.env`
- Never commit secrets
- Avoid premature abstractions
- One responsibility per module
- Prefer readable code over clever code

---

## Storage

SQLite tables:
- news_items
- digest_runs
- sent_links

Use hashes to avoid duplicate news.

---

## Environment

```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

OPENAI_API_KEY=
ANTHROPIC_API_KEY=

DIGEST_TIME=08:30
TIMEZONE=Europe/Amsterdam
```

---

## MVP Goals

1. Collect RSS feeds
2. Generate digest
3. Send Telegram message
4. Prevent duplicates
5. Run every morning automatically

Do not implement yet:
- web UI
- multi-user support
- vector DB
- RAG
- browser automation
- subscriptions
- complex admin panel