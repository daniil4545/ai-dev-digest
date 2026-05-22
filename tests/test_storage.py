from src.models import NewsItem
from src.storage import Storage


def _make_item(title: str = "Test", url: str = "https://example.com") -> NewsItem:
    return NewsItem(
        title=title,
        url=url,
        source="test",
        published_at="2025-01-01T00:00:00",
        summary="test summary",
    )


class TestStorage:
    def test_init_creates_tables(self) -> None:
        storage = Storage(":memory:")
        try:
            tables = storage._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            names = [r["name"] for r in tables]
            assert "news_items" in names
            assert "digest_runs" in names
            assert "sent_links" in names
        finally:
            storage.close()

    def test_save_and_retrieve_item(self) -> None:
        storage = Storage(":memory:")
        try:
            item = _make_item()
            storage.save_item(item)
            items = storage.get_recent_items()
            assert len(items) == 1
            assert items[0].title == "Test"
            assert items[0].url == "https://example.com"
        finally:
            storage.close()

    def test_duplicate_detection(self) -> None:
        storage = Storage(":memory:")
        try:
            item = _make_item()
            storage.save_item(item)
            assert not storage.is_duplicate(_make_item(title="Other"))

            assert storage.is_duplicate(item)
            storage.save_item(item)
            items = storage.get_recent_items()
            assert len(items) == 1
        finally:
            storage.close()

    def test_save_run(self) -> None:
        storage = Storage(":memory:")
        try:
            run_id = storage.save_run(item_count=5, status="success")
            assert isinstance(run_id, int)
            assert run_id > 0
        finally:
            storage.close()

    def test_was_link_sent(self) -> None:
        storage = Storage(":memory:")
        try:
            url = "https://example.com/article"
            assert not storage.was_link_sent(url)

            storage._conn.execute("INSERT INTO sent_links (url) VALUES (?)", (url,))
            storage._conn.commit()
            assert storage.was_link_sent(url)
        finally:
            storage.close()

    def test_empty_db(self) -> None:
        storage = Storage(":memory:")
        try:
            assert storage.get_recent_items() == []
        finally:
            storage.close()
