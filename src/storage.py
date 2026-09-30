import sqlite3
from pathlib import Path


class Storage:
    """SQLite table of links that already appeared in a digest."""

    def __init__(self, db_path: str = ":memory:") -> None:
        """Initialise storage, open database connection and create tables.

        Args:
            db_path: filesystem path to the SQLite database file, or
                ``\":memory:\"`` for an in-memory database (default).
        """
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._create_tables()

    def _create_tables(self) -> None:
        """Create the sent_links table if it does not exist."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS sent_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                sent_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
        self._conn.commit()

    def mark_link_sent(self, url: str) -> None:
        """Record a URL as already in a digest.

        Args:
            url: the link URL to record.
        """
        self._conn.execute("INSERT OR IGNORE INTO sent_links (url) VALUES (?)", (url,))
        self._conn.commit()

    def was_link_sent(self, url: str) -> bool:
        """Check whether a URL has already appeared in a digest.

        Args:
            url: the link to check.

        Returns:
            ``True`` if the URL exists in ``sent_links``.
        """
        row = self._conn.execute(
            "SELECT 1 FROM sent_links WHERE url = ?", (url,)
        ).fetchone()
        return row is not None

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()
