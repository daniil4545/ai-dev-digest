import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import feedparser
import requests
from bs4 import BeautifulSoup

from src.models import NewsItem
from src.sources import SOURCES

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15
MAX_ITEMS_PER_SOURCE = 50


def _parse_date(date_tuple: Any) -> str:
    if date_tuple is None:
        return datetime.now(UTC).isoformat()
    try:
        dt = datetime(*date_tuple[:6], tzinfo=UTC)
        return dt.isoformat()
    except (TypeError, ValueError):
        return datetime.now(UTC).isoformat()


def _truncate(text: str, max_len: int = 500) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(" ", 1)[0] + "..."


def normalize_url(url: str) -> str:
    """Lowercase the host, drop utm_* and the trailing slash: one article, one URL."""
    parts = urlsplit(url.strip())
    query = parts.query
    if "utm_" in query:
        # Rebuild only when needed: re-encoding could change other parameters
        pairs = parse_qsl(query, keep_blank_values=True)
        query = urlencode([(k, v) for k, v in pairs if not k.startswith("utm_")])
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, query, ""))


def _filter_recent(items: list[NewsItem], hours: int = 24) -> list[NewsItem]:
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    filtered = []
    for item in items:
        try:
            published = datetime.fromisoformat(item.published_at)
            if published.tzinfo is None:
                published = published.replace(tzinfo=UTC)
            if published >= cutoff:
                filtered.append(item)
        except (ValueError, TypeError):
            filtered.append(item)
    if filtered:
        logger.info(
            "Time filter: %d / %d items are newer than %d hours",
            len(filtered),
            len(items),
            hours,
        )
    return filtered


def fetch_rss(url: str) -> list[NewsItem]:
    try:
        headers = {"User-Agent": "ai-dev-digest-bot/1.0"}
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        feed = feedparser.parse(response.text)
        if feed.bozo and not feed.entries:
            logger.warning("Failed to parse RSS feed %s: %s", url, feed.bozo_exception)
            return []
    except requests.RequestException as e:
        logger.warning("Failed to fetch RSS feed %s: %s", url, e)
        return []
    except Exception as e:
        logger.warning("Failed to parse RSS feed %s: %s", url, e)
        return []

    items: list[NewsItem] = []
    for entry in feed.entries:
        title = getattr(entry, "title", "")
        link = getattr(entry, "link", "")
        summary = getattr(entry, "summary", getattr(entry, "description", ""))
        summary = BeautifulSoup(summary, "html.parser").get_text(" ", strip=True)
        # Atom feeds may carry only <updated>; without it the entry is always "now"
        published = _parse_date(
            entry.get("published_parsed") or entry.get("updated_parsed")
        )
        items.append(
            NewsItem(
                title=title,
                url=link,
                source="",
                published_at=published,
                summary=_truncate(summary),
            )
        )
    return items


def fetch_hn_top() -> list[NewsItem]:
    try:
        response = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        story_ids = response.json()[:30]
    except requests.RequestException as e:
        logger.warning("Failed to fetch HN top stories: %s", e)
        return []

    items: list[NewsItem] = []
    for sid in story_ids:
        try:
            resp = requests.get(
                f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            if not data or not data.get("title"):
                continue
            title = data["title"]
            url = data.get("url", f"https://news.ycombinator.com/item?id={sid}")
            score = float(data.get("score", 0))
            published_at = datetime.fromtimestamp(
                data.get("time", 0), tz=UTC
            ).isoformat()
            items.append(
                NewsItem(
                    title=title,
                    url=url,
                    source="",
                    published_at=published_at,
                    summary=_truncate(title),
                    score=score,
                )
            )
        except (requests.RequestException, ValueError, TypeError) as e:
            logger.warning("Failed to fetch HN item %s: %s", sid, e)
            continue
    return items


def fetch_github_trending(url: str) -> list[NewsItem]:
    try:
        headers = {"User-Agent": "ai-dev-digest-bot/1.0"}
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.warning("Failed to fetch GitHub trending: %s", e)
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    items: list[NewsItem] = []
    for article in soup.select("article.Box-row"):
        h2 = article.select_one("h2")
        if not h2:
            continue
        a = h2.select_one("a")
        if not a:
            continue
        repo_path = str(a.get("href", ""))
        if repo_path.startswith("/"):
            repo_path = f"https://github.com{repo_path}"
        repo_name = "".join(a.text.split())

        desc_el = article.select_one("p")
        description = desc_el.text.strip() if desc_el else ""

        stars_el = article.select_one("a.Link--muted")
        stars = 0.0
        if stars_el:
            try:
                stars_text = stars_el.text.strip().replace(",", "")
                stars = float(stars_text) if stars_text else 0.0
            except ValueError:
                stars = 0.0

        published_at = datetime.now(UTC).isoformat()
        items.append(
            NewsItem(
                title=repo_name,
                url=repo_path,
                source="",
                published_at=published_at,
                summary=_truncate(description),
                score=stars,
            )
        )
    return items


FETCH_MAP: dict[str, Callable[..., list[NewsItem]]] = {
    "rss": fetch_rss,
    "hn_api": fetch_hn_top,
    "github_trending": fetch_github_trending,
}


def collect_all(max_item_hours: int = 72) -> list[NewsItem]:
    all_items: list[NewsItem] = []
    for source in SOURCES:
        fetcher = FETCH_MAP.get(source.type)
        if fetcher is None:
            logger.warning("Unknown source type: %s for %s", source.type, source.name)
            continue
        try:
            if source.type == "hn_api":
                items = fetcher()
            else:
                items = fetcher(source.url)

            items = items[:MAX_ITEMS_PER_SOURCE]
            for item in items:
                item.source = source.name
                item.url = normalize_url(item.url)
            logger.info("Collected %d items from %s", len(items), source.name)
            all_items.extend(items)
        except requests.RequestException as e:
            logger.warning("Failed to fetch %s: %s", source.name, e)
        except Exception as e:
            logger.warning("Unexpected error fetching %s: %s", source.name, e)

    all_items = _filter_recent(all_items, hours=max_item_hours)
    return all_items
