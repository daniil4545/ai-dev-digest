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
            lines.append(f"{index}. {item.title}")
            lines.append(f"   {item.why_it_matters}")
            lines.append(f"   → {item.action}: {item.url}")
            lines.append("")

    return "\n".join(lines).strip()


def format_digest_message(items: List[NewsItem]) -> str:
    body = build_digest(items)
    if not body:
        return ""

    return f"*🤖 AI Dev Digest*\n{body}\n\n--- "
