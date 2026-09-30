from src.storage import Storage


class TestStorage:
    def test_link_is_remembered_after_mark(self) -> None:
        storage = Storage(":memory:")
        try:
            url = "https://example.com/article"
            assert not storage.was_link_sent(url)

            storage.mark_link_sent(url)
            storage.mark_link_sent(url)

            assert storage.was_link_sent(url)
        finally:
            storage.close()

    def test_links_survive_reopen(self, tmp_path) -> None:
        db_path = str(tmp_path / "nested" / "digest.db")
        storage = Storage(db_path)
        storage.mark_link_sent("https://example.com/a")
        storage.close()

        reopened = Storage(db_path)
        try:
            assert reopened.was_link_sent("https://example.com/a")
        finally:
            reopened.close()
