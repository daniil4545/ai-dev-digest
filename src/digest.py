import re
from typing import Dict, List

from src.models import NewsItem
from src.sources import SOURCES

CATEGORY_HEADERS: Dict[str, str] = {
    "ai-news": "🔥 Main Updates",
    "tools": "🧰 New Tools",
    "trending": "⭐ Trending",
    "dev-news": "📡 Dev News",
    "community": "💬 Community",
}

CATEGORY_ORDER: List[str] = [
    "ai-news",
    "tools",
    "trending",
    "dev-news",
    "community",
    "other",
]

_source_to_category: Dict[str, str] = {}
for s in SOURCES:
    _source_to_category[s.name] = s.category


def _get_category(source: str) -> str:
    return _source_to_category.get(source, "other")


def _clean_title(title: str) -> str:
    return " ".join(title.replace("\n", " ").split())


def _short_title(title: str, max_words: int = 5) -> str:
    words = _clean_title(title).split()
    words = [w.rstrip("/") for w in words]
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words]) + "..."


def _shorten(text: str, max_sentences: int = 2, max_chars: int = 150) -> str:
    if not text:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    short = " ".join(sentences[:max_sentences])
    if len(short) > max_chars:
        short = short[: max_chars - 3].rsplit(" ", 1)[0] + "..."
    return short


def _escape_markdown(text: str) -> str:
    return re.sub(r"([_*`\[])", r"\\\1", text)


def build_digest(items: List[NewsItem]) -> str:
    if not items:
        return ""

    sorted_items = sorted(items, key=lambda x: x.score, reverse=True)

    grouped: Dict[str, List[NewsItem]] = {}
    for item in sorted_items:
        cat = _get_category(item.source)
        grouped.setdefault(cat, []).append(item)

    lines: List[str] = []
    index = 0

    for cat in CATEGORY_ORDER:
        group = grouped.get(cat)
        if not group:
            continue

        header = CATEGORY_HEADERS.get(cat, "📌 Other")
        lines.append(header)
        lines.append("")

        for item in group:
            index += 1
            title = _escape_markdown(_short_title(item.title))
            summary = (item.why_it_matters or "").strip()
            cleaned_title = _clean_title(item.title).lower()
            if summary.lower().startswith(cleaned_title):
                summary = ""
            if len(summary) > 600:
                summary = summary[:597].rsplit(" ", 1)[0] + "..."
            lines.append(f"{index}. {title}")
            if summary:
                lines.append(f"   {_escape_markdown(summary)}")
            if item.action:
                lines.append(f"   Action: {_escape_markdown(item.action.strip())}")
            lines.append(f"   🔗 {_escape_markdown(item.url)}")
            lines.append("")

    return "\n".join(lines).strip()


def format_digest_message(items: List[NewsItem]) -> str:
    body = build_digest(items)
    if not body:
        return ""

    return f"*🤖 AI Dev Digest*\n{body}\n\n---"
