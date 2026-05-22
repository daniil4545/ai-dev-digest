import logging
from datetime import datetime, timezone
from typing import Any, Callable, List

import feedparser
import requests
from bs4 import BeautifulSoup

from src.models import NewsItem
from src.sources import SOURCES

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15


def _parse_date(date_tuple: Any) -> str:
    if date_tuple is None:
        return datetime.now(timezone.utc).isoformat()
    try:
        dt = datetime(*date_tuple[:6], tzinfo=timezone.utc)
        return dt.isoformat()
    except (TypeError, ValueError):
        return datetime.now(timezone.utc).isoformat()


def _truncate(text: str, max_len: int = 500) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(" ", 1)[0] + "..."


def fetch_rss(url: str) -> List[NewsItem]:
    try:
        feed = feedparser.parse(url)
        if feed.bozo and not feed.entries:
            logger.warning("Failed to parse RSS feed %s: %s", url, feed.bozo_exception)
            return []
    except Exception as e:
        logger.warning("Failed to fetch RSS feed %s: %s", url, e)
        return []

    items: List[NewsItem] = []
    for entry in feed.entries:
        title = getattr(entry, "title", "")
        link = getattr(entry, "link", "")
        summary = getattr(entry, "summary", getattr(entry, "description", ""))
        published = _parse_date(entry.get("published_parsed"))
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


def fetch_hn_top() -> List[NewsItem]:
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

    items: List[NewsItem] = []
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
                data.get("time", 0), tz=timezone.utc
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
        except requests.RequestException:
            logger.warning("Failed to fetch HN item %s", sid)
            continue
    return items


def fetch_reddit_hot(url: str) -> List[NewsItem]:
    try:
        headers = {"User-Agent": "ai-dev-digest-bot/1.0"}
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        logger.warning("Failed to fetch Reddit %s: %s", url, e)
        return []

    items: List[NewsItem] = []
    for child in data.get("data", {}).get("children", []):
        post = child.get("data", {})
        title = str(post.get("title", ""))
        post_url = str(post.get("url", ""))
        if not post_url or post_url.startswith("https://www.reddit.com/r/"):
            post_url = f"https://www.reddit.com{post.get('permalink', '')}"
        score = float(post.get("score", 0))
        created = post.get("created_utc", 0)
        published_at = datetime.fromtimestamp(created, tz=timezone.utc).isoformat()
        items.append(
            NewsItem(
                title=title,
                url=post_url,
                source="",
                published_at=published_at,
                summary=_truncate(post.get("selftext", title)),
                score=score,
            )
        )
    return items


def fetch_github_trending(url: str) -> List[NewsItem]:
    try:
        headers = {"User-Agent": "ai-dev-digest-bot/1.0"}
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.warning("Failed to fetch GitHub trending: %s", e)
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    items: List[NewsItem] = []
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
        repo_name = a.text.strip().replace(" ", "")

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

        published_at = datetime.now(timezone.utc).isoformat()
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


FETCH_MAP: dict[str, Callable[..., List[NewsItem]]] = {
    "rss": fetch_rss,
    "hn_api": fetch_hn_top,
    "reddit_api": fetch_reddit_hot,
    "github_trending": fetch_github_trending,
}


def collect_all() -> List[NewsItem]:
    all_items: List[NewsItem] = []
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
            for item in items:
                item.source = source.name
            logger.info("Collected %d items from %s", len(items), source.name)
            all_items.extend(items)
        except requests.RequestException as e:
            logger.warning("Failed to fetch %s: %s", source.name, e)
        except Exception as e:
            logger.warning("Unexpected error fetching %s: %s", source.name, e)
    return all_items
