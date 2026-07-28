import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from src.models import NewsItem


class Storage:
    """SQLite-backed storage for news items, digest runs and sent links.

    Handles duplicate detection via MD5 hash of ``title + url`` and
    provides convenience methods for the common data access patterns
    used by the digest pipeline.
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        """Initialise storage, open database connection and create tables.

        Args:
            db_path: filesystem path to the SQLite database file, or
                ``\":memory:\"`` for an in-memory database (default).
        """
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        """Create the three required tables if they do not exist."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS news_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                source TEXT NOT NULL,
                published_at TEXT NOT NULL,
                summary TEXT NOT NULL,
                score REAL DEFAULT 0.0,
                why_it_matters TEXT DEFAULT '',
                action TEXT DEFAULT '',
                hash TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS digest_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_at TEXT NOT NULL DEFAULT (datetime('now')),
                item_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending'
            );

            CREATE TABLE IF NOT EXISTS sent_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                sent_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
        self._conn.commit()

    @staticmethod
    def _compute_hash(title: str, url: str) -> str:
        """Return MD5 hex digest for duplicate detection.

        Args:
            title: item title.
            url: item URL.

        Returns:
            32-character MD5 hex digest.
        """
        raw = url.strip().lower().encode("utf-8")
        return hashlib.md5(raw).hexdigest()

    def save_item(self, item: NewsItem) -> int:
        """Persist a news item, ignoring duplicates.

        Duplicates are detected by URL hash;
        if the same hash already exists the row is silently skipped.

        Args:
            item: the news item to persist.

        Returns:
            row id of the inserted or existing row.
        """
        item_hash = self._compute_hash(item.title, item.url)
        cur = self._conn.execute(
            """INSERT OR IGNORE INTO news_items
               (title, url, source, published_at, summary, score,
                why_it_matters, action, hash)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                item.title,
                item.url,
                item.source,
                item.published_at,
                item.summary,
                item.score,
                item.why_it_matters,
                item.action,
                item_hash,
            ),
        )
        self._conn.commit()

        if cur.rowcount == 1 and cur.lastrowid is not None:
            return cur.lastrowid

        row = self._conn.execute(
            "SELECT id FROM news_items WHERE hash = ?", (item_hash,)
        ).fetchone()
        return row["id"] if row is not None else -1

    def is_duplicate(self, item: NewsItem) -> bool:
        """Check whether an item already exists in the database.

        Args:
            item: the news item to check.

        Returns:
            ``True`` if the item's hash is already stored.
        """
        item_hash = self._compute_hash(item.title, item.url)
        row = self._conn.execute(
            "SELECT 1 FROM news_items WHERE hash = ?", (item_hash,)
        ).fetchone()
        return row is not None

    def save_run(self, item_count: int, status: str) -> int:
        """Record a digest run and return its row id.

        Args:
            item_count: number of items included in the digest.
            status: run status (e.g. ``\"success\"``, ``\"failed\"``).

        Returns:
            row id of the newly inserted run.
        """
        now = datetime.now(timezone.utc).isoformat()
        cur = self._conn.execute(
            "INSERT INTO digest_runs (run_at, item_count, status) VALUES (?, ?, ?)",
            (now, item_count, status),
        )
        self._conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def mark_link_sent(self, url: str) -> None:
        """Record a URL as already sent.

        Args:
            url: the link URL to record.
        """
        self._conn.execute("INSERT OR IGNORE INTO sent_links (url) VALUES (?)", (url,))
        self._conn.commit()

    def was_link_sent(self, url: str) -> bool:
        """Check whether a URL has already been sent in a previous digest.

        Args:
            url: the link to check.

        Returns:
            ``True`` if the URL exists in ``sent_links``.
        """
        row = self._conn.execute(
            "SELECT 1 FROM sent_links WHERE url = ?", (url,)
        ).fetchone()
        return row is not None

    def get_recent_items(self, limit: int = 50) -> List[NewsItem]:
        """Return the most recent news items ordered by ``created_at`` desc.

        Args:
            limit: maximum number of items to return (default 50).

        Returns:
            list of ``NewsItem`` instances.
        """
        columns = [
            "title",
            "url",
            "source",
            "published_at",
            "summary",
            "score",
            "why_it_matters",
            "action",
        ]
        query = f"SELECT {', '.join(columns)} FROM news_items ORDER BY created_at DESC LIMIT ?"
        rows = self._conn.execute(query, (limit,)).fetchall()
        return [NewsItem(**dict(r)) for r in rows]

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()
