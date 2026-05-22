import json
import logging
import re
from typing import Any, List

import ollama

from src.config import get_config
from src.digest import _shorten
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
        f"Верни JSON: {{\"score\": 0-5, \"summary\": \"краткое саммари новости (1-2 предложения, о чём статья)\"}}\n"
        f"Новость: {text}"
    )


def _heuristic_score(item: NewsItem) -> NewsItem:
    text = f"{item.title} {item.summary}".lower()
    matched = []
    for kw in KEYWORDS:
        if kw in text:
            matched.append(kw)
    if matched:
        logger.info("Heuristic match for '%s': keywords %s", item.title, matched)
        item.score = 3.0
        item.why_it_matters = _shorten(item.summary or item.title)
        item.action = ""
        return item
    logger.debug("No heuristic keywords in '%s'", item.title)
    item.score = 1.0
    item.why_it_matters = ""
    item.action = ""
    return item


def _clean_json_string(s: str) -> str:
    """Fix common LLM JSON formatting issues (trailing commas, single quotes, Python booleans)."""
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
            label, e.pos, e.msg,
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
            "%s (strict=False): %s", label, e,
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

            result = _try_json_load_strict(candidate_inner, "fence+braces (strict=False)")
            if result is not None:
                return result

    logger.warning(
        "All JSON extraction attempts failed for content (%d chars). "
        "First 200 chars: %.200s",
        len(content), content,
    )
    raise json.JSONDecodeError("Could not extract JSON", content, 0)


def score_news(items: List[NewsItem]) -> List[NewsItem]:
    config = get_config()
    client = ollama.Client(host=config.ollama_host)
    logger.info("Scoring %d news items", len(items))

    total = len(items)
    scored: List[NewsItem] = []
    needs_llm: List[NewsItem] = []
    needs_llm_idx: List[int] = []

    for idx, item in enumerate(items):
        candidate = _heuristic_score(item)
        if candidate.score >= 3.0:
            logger.info("[%d/%d] Heuristic pass for '%s' (keywords)", idx + 1, total, item.title)
            scored.append(candidate)
        else:
            needs_llm.append(item)
            needs_llm_idx.append(idx)

    if not needs_llm:
        logger.info("All items passed heuristic, LLM not needed")
        return scored

    logger.info(
        "Heuristic pass: %d passed, %d need LLM scoring",
        len(scored), len(needs_llm),
    )

    for pos, (item, original_idx) in enumerate(zip(needs_llm, needs_llm_idx)):
        try:
            prompt = _build_prompt(item)
            logger.debug(
                "[LLM %d/%d] Sending: %s", pos + 1, len(needs_llm), item.title
            )
            response = client.chat(
                model=config.ollama_model,
                messages=[{"role": "user", "content": prompt}],
                options={"num_predict": 256},
            )
            content = response["message"]["content"]
            data = _extract_json(content)
            item.score = float(data.get("score", 0.0))
            item.why_it_matters = data.get("summary") or ""
            item.action = ""
            logger.info(
                "[LLM %d/%d] '%s' = %.1f | summary: %s",
                pos + 1, len(needs_llm), item.title, item.score,
                item.why_it_matters[:100] if item.why_it_matters else "(none)",
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            logger.warning(
                "[LLM %d/%d] Failed to parse for '%s', heuristic=1.0 stays",
                pos + 1, len(needs_llm), item.title,
            )
        except Exception as e:
            logger.warning(
                "[LLM %d/%d] Error for '%s': %s, heuristic=1.0 stays",
                pos + 1, len(needs_llm), item.title, e,
            )

        if item.score >= 3.0:
            scored.append(item)

    logger.info("Scoring complete: %d / %d passed", len(scored), total)
    return scored


def score_news_batch(items: List[NewsItem]) -> List[NewsItem]:
    config = get_config()
    client = ollama.Client(host=config.ollama_host)
    logger.info("Batch scoring %d news items", len(items))

    scored: List[NewsItem] = []
    needs_llm: List[NewsItem] = []

    for item in items:
        candidate = _heuristic_score(item)
        if candidate.score >= 3.0:
            scored.append(candidate)
        else:
            needs_llm.append(item)

    if not needs_llm:
        logger.info("All items passed heuristic, LLM not needed")
        return scored

    logger.info(
        "Heuristic pass: %d passed, %d need LLM batch scoring",
        len(scored), len(needs_llm),
    )

    try:
        batch_prompt = (
            "Rate these news for a developer interested in AI coding tools.\n"
            'Return JSON array: [{"score": 0-5, "summary": "краткое саммари (1-2 предложения, о чём статья)"}, ...]\n\n'
        )
        for i, item in enumerate(needs_llm):
            batch_prompt += f"{i + 1}. {item.title} — {item.summary}\n"

        logger.debug("Batch prompt (%d chars, %d items)", len(batch_prompt), len(needs_llm))
        response = client.chat(
            model=config.ollama_model,
            messages=[{"role": "user", "content": batch_prompt}],
            options={"num_predict": 1024},
        )
        content = response["message"]["content"]
        data = _extract_json(content)
        if isinstance(data, list) and len(data) == len(needs_llm):
            logger.debug("Batch response has %d items, applying scores", len(data))
            for item, result in zip(needs_llm, data):
                item.score = float(result.get("score", 0.0))
                item.why_it_matters = result.get("summary") or ""
                item.action = ""
                logger.info(
                    "Batch scored '%s' = %.1f", item.title, item.score,
                )
            for item in needs_llm:
                if item.score >= 3.0:
                    scored.append(item)
            logger.info(
                "Batch scoring complete: %d / %d passed", len(scored), len(items)
            )
            return scored
        logger.warning(
            "Batch response format invalid: expected list of %d, got %s (type=%s)",
            len(needs_llm), content[:200], type(data).__name__,
        )
    except Exception as e:
        logger.warning("Batch scoring failed: %s, falling back to sequential", e)

    logger.info("Falling back to sequential LLM for %d items", len(needs_llm))
    for item in needs_llm:
        try:
            prompt = _build_prompt(item)
            response = client.chat(
                model=config.ollama_model,
                messages=[{"role": "user", "content": prompt}],
                options={"num_predict": 256},
            )
            content = response["message"]["content"]
            data = _extract_json(content)
            item.score = float(data.get("score", 0.0))
            item.why_it_matters = data.get("summary") or ""
            item.action = ""
            logger.info(
                "LLM scored '%s' = %.1f", item.title, item.score,
            )
        except Exception:
            logger.debug("LLM failed for '%s', keeping heuristic=1.0", item.title)

        if item.score >= 3.0:
            scored.append(item)

    logger.info("Scoring complete: %d / %d passed", len(scored), len(items))
    return scored
