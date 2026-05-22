import json
import logging
from typing import List

import ollama

from src.config import get_config
from src.models import NewsItem

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30

KEYWORDS = frozenset(
    {
        "claude",
        "codex",
        "opencode",
        "mcp",
        "agent",
        "llm",
        "gpt",
        "release",
    }
)


def _contains_cyrillic(text: str) -> bool:
    for ch in text:
        if "\u0400" <= ch <= "\u04ff" or "\u0500" <= ch <= "\u052f":
            return True
    return False


def _build_prompt(item: NewsItem) -> str:
    text = f"{item.title} — {item.summary}"
    if _contains_cyrillic(text):
        return (
            f"Оцени новость для разработчика, интересующегося AI coding tools.\n"
            f'Верни JSON: {{"score": 0-5, "why_it_matters": "почему это важно", "action": "что делать"}}\n'
            f"Новость: {text}"
        )
    return (
        f"Rate this news for a developer interested in AI coding tools.\n"
        f'Return JSON: {{"score": 0-5, "why_it_matters": "why it matters", "action": "what to do"}}\n'
        f"News: {text}"
    )


def _heuristic_score(item: NewsItem) -> NewsItem:
    text = f"{item.title} {item.summary}".lower()
    for kw in KEYWORDS:
        if kw in text:
            item.score = 3.0
            item.why_it_matters = "Matched heuristic keywords"
            item.action = "Read more"
            return item
    item.score = 1.0
    item.why_it_matters = ""
    item.action = ""
    return item


def score_news(items: List[NewsItem]) -> List[NewsItem]:
    config = get_config()
    client = ollama.Client(host=config.ollama_host)

    scored: List[NewsItem] = []
    for item in items:
        try:
            prompt = _build_prompt(item)
            response = client.chat(
                model=config.ollama_model,
                messages=[{"role": "user", "content": prompt}],
                options={"num_predict": 256},
            )
            content = response["message"]["content"]
            data = json.loads(content)
            item.score = float(data.get("score", 0.0))
            item.why_it_matters = data.get("why_it_matters") or ""
            item.action = data.get("action") or ""
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            logger.warning("Failed to parse Ollama response for: %s", item.title)
            item = _heuristic_score(item)
        except Exception as e:
            logger.warning("Ollama error for '%s': %s", item.title, e)
            item = _heuristic_score(item)

        if item.score >= 3.0:
            scored.append(item)

    return scored


def score_news_batch(items: List[NewsItem]) -> List[NewsItem]:
    config = get_config()
    client = ollama.Client(host=config.ollama_host)

    try:
        batch_prompt = (
            "Rate these news for a developer interested in AI coding tools.\n"
            'Return JSON array: [{"score": 0-5, "why_it_matters": "...", "action": "..."}, ...]\n\n'
        )
        for i, item in enumerate(items):
            batch_prompt += f"{i + 1}. {item.title} — {item.summary}\n"

        response = client.chat(
            model=config.ollama_model,
            messages=[{"role": "user", "content": batch_prompt}],
            options={"num_predict": 1024},
        )
        content = response["message"]["content"]
        data = json.loads(content)
        if isinstance(data, list) and len(data) == len(items):
            for item, result in zip(items, data):
                item.score = float(result.get("score", 0.0))
                item.why_it_matters = result.get("why_it_matters") or ""
                item.action = result.get("action") or ""
            return [item for item in items if item.score >= 3.0]
        logger.warning(
            "Batch response format invalid: expected list of %d, got %s",
            len(items), type(data).__name__,
        )
    except Exception:
        logger.warning("Batch scoring failed, falling back to sequential scoring")

    return score_news(items)
