import json
import logging
import re
from typing import Any

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


def _build_prompt(item: NewsItem) -> str:
    text = f"{item.title} — {item.summary}"
    return (
        f"Оцени новость для разработчика, интересующегося AI coding tools.\n"
        'Верни JSON: {"score": 0-5, "title": "короткий заголовок (2-5 слов, '
        'по-русски)", "summary": "краткое содержание на русском (до 100 слов, '
        'связный текст)"}\n'
        f"Новость: {text}"
    )


def _shorten_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rsplit(" ", 1)[0] + "..."


def _heuristic_fallback(item: NewsItem) -> NewsItem:
    text = f"{item.title} {item.summary}".lower()
    for kw in KEYWORDS:
        if kw in text:
            logger.info("Heuristic fallback for '%s': keyword %s", item.title, kw)
            item.score = 3.0
            item.title = _shorten_text(item.title, max_chars=80)
            item.why_it_matters = _shorten_text(
                item.summary or item.title, max_chars=300
            )
            return item
    item.score = 1.0
    return item


def _heuristic_score(item: NewsItem) -> NewsItem:
    return _heuristic_fallback(item)


def _clamp_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(score, 5.0))


def _apply_llm_result(item: NewsItem, data: dict) -> None:
    item.score = _clamp_score(data.get("score", 0.0))
    item.title = str(data.get("title", item.title))
    item.why_it_matters = data.get("summary") or ""


def _clean_json_string(s: str) -> str:
    """Fix common LLM JSON formatting issues.

    Handles trailing commas, single quotes and Python booleans.
    """
    s = re.sub(r",\s*}", "}", s)
    s = re.sub(r",\s*]", "]", s)
    s = s.replace("None", "null").replace("True", "true").replace("False", "false")
    if not re.search(r'[^\\]"', s):
        s = s.replace("'", '"')
    return s


def _try_json_load(s: str, label: str) -> Any | None:
    """Try loading JSON, log error details on failure."""
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        logger.debug(
            "%s: JSON parse error at pos %d: %s",
            label,
            e.pos,
            e.msg,
        )
        return None


def _try_json_load_strict(s: str, label: str) -> Any | None:
    """Try loading JSON with strict=False (allows control chars in strings)."""
    try:
        decoder = json.JSONDecoder(strict=False)
        obj, _ = decoder.raw_decode(s)
        return obj
    except (json.JSONDecodeError, ValueError) as e:
        logger.debug(
            "%s (strict=False): %s",
            label,
            e,
        )
        return None


def _extract_json(content: str) -> Any:
    content = content.strip().strip("\ufeff")
    logger.debug("Raw Ollama response (%d chars): %s", len(content), content)

    cleaned = _clean_json_string(content)
    if cleaned != content:
        logger.debug("Cleaned JSON string (trailing commas / quotes / Python booleans)")

    result = _try_json_load(cleaned, "clean")
    if result is not None:
        return result

    result = _try_json_load_strict(cleaned, "clean (strict=False)")
    if result is not None:
        return result

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = _clean_json_string(cleaned[start : end + 1])
        logger.debug("Curly-brace candidate (%d chars): %s", len(candidate), candidate)

        result = _try_json_load(candidate, "curly-brace")
        if result is not None:
            logger.debug("Parsed via curly-brace extraction (skipped %d chars)", start)
            return result

        result = _try_json_load_strict(candidate, "curly-brace (strict=False)")
        if result is not None:
            return result

    if cleaned.startswith("```"):
        logger.debug("Trying markdown code fence extraction")
        lines = cleaned.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        inner = _clean_json_string("\n".join(lines).strip())

        result = _try_json_load(inner, "code-fence")
        if result is not None:
            logger.debug("Parsed inside code fence")
            return result

        result = _try_json_load_strict(inner, "code-fence (strict=False)")
        if result is not None:
            return result

        start = inner.find("{")
        end = inner.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate_inner = _clean_json_string(inner[start : end + 1])

            result = _try_json_load(candidate_inner, "fence+braces")
            if result is not None:
                logger.debug("Parsed via braces inside code fence")
                return result

            result = _try_json_load_strict(
                candidate_inner, "fence+braces (strict=False)"
            )
            if result is not None:
                return result

    logger.warning(
        "All JSON extraction attempts failed for content (%d chars). "
        "First 200 chars: %.200s",
        len(content),
        content,
    )
    raise json.JSONDecodeError("Could not extract JSON", content, 0)


def score_news(items: list[NewsItem]) -> list[NewsItem]:
    config = get_config()
    client = ollama.Client(host=config.ollama_host, timeout=REQUEST_TIMEOUT)
    logger.info("Scoring %d news items (all go through LLM)", len(items))

    total = len(items)
    scored: list[NewsItem] = []

    for idx, item in enumerate(items):
        try:
            prompt = _build_prompt(item)
            response = client.chat(
                model=config.ollama_model,
                messages=[{"role": "user", "content": prompt}],
                options={"num_predict": 512},
            )
            content = response["message"]["content"]
            data = _extract_json(content)
            _apply_llm_result(item, data)
            logger.info(
                "[%d/%d] '%s' = %.1f | summary: %s",
                idx + 1,
                total,
                item.title,
                item.score,
                item.why_it_matters[:80] if item.why_it_matters else "(none)",
            )
        except Exception as e:
            logger.warning(
                "[%d/%d] LLM failed for '%s': %s, heuristic fallback",
                idx + 1,
                total,
                item.title,
                e,
            )
            _heuristic_fallback(item)

        if item.score >= 3.0:
            scored.append(item)

    logger.info("Scoring complete: %d / %d passed", len(scored), total)
    return scored


def score_news_batch(items: list[NewsItem]) -> list[NewsItem]:
    config = get_config()
    client = ollama.Client(host=config.ollama_host, timeout=REQUEST_TIMEOUT)
    logger.info("Batch scoring %d news items", len(items))

    scored: list[NewsItem] = []

    try:
        batch_prompt = (
            "Rate these news for a developer interested in AI coding tools.\n"
            'Return JSON array: [{"score": 0-5, "title": "короткий заголовок '
            '(2-5 слов, по-русски)", "summary": "краткое содержание на русском '
            '(до 100 слов, связный текст)"}, ...]\n\n'
        )
        for i, item in enumerate(items):
            batch_prompt += f"{i + 1}. {item.title} — {item.summary}\n"

        logger.debug("Batch prompt (%d chars, %d items)", len(batch_prompt), len(items))
        response = client.chat(
            model=config.ollama_model,
            messages=[{"role": "user", "content": batch_prompt}],
            options={"num_predict": 1024},
        )
        content = response["message"]["content"]
        data = _extract_json(content)
        if isinstance(data, list) and len(data) == len(items):
            logger.debug("Batch response has %d items, applying scores", len(data))
            for item, result in zip(items, data):
                _apply_llm_result(item, result)
                logger.info(
                    "Batch scored '%s' = %.1f",
                    item.title,
                    item.score,
                )
            for item in items:
                if item.score >= 3.0:
                    scored.append(item)
            logger.info(
                "Batch scoring complete: %d / %d passed", len(scored), len(items)
            )
            return scored
        logger.warning(
            "Batch response format invalid: expected list of %d, got %s (type=%s)",
            len(items),
            content[:200],
            type(data).__name__,
        )
    except Exception as e:
        logger.warning("Batch scoring failed: %s, falling back to sequential", e)

    logger.info("Falling back to sequential LLM for %d items", len(items))
    for idx, item in enumerate(items):
        try:
            prompt = _build_prompt(item)
            response = client.chat(
                model=config.ollama_model,
                messages=[{"role": "user", "content": prompt}],
                options={"num_predict": 512},
            )
            content = response["message"]["content"]
            data = _extract_json(content)
            _apply_llm_result(item, data)
            logger.info(
                "[%d/%d] '%s' = %.1f",
                idx + 1,
                len(items),
                item.title,
                item.score,
            )
        except Exception as e:
            logger.warning(
                "[%d/%d] LLM failed for '%s': %s, heuristic fallback",
                idx + 1,
                len(items),
                item.title,
                e,
            )
            _heuristic_fallback(item)

        if item.score >= 3.0:
            scored.append(item)

    logger.info("Scoring complete: %d / %d passed", len(scored), len(items))
    return scored
