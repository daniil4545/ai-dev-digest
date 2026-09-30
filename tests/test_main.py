import json

import pytest

import src.main
from src.main import collect_candidates, main, mark_digest
from src.models import NewsItem
from src.storage import Storage


def _item(url: str, title: str = "Title") -> NewsItem:
    return NewsItem(
        title=title,
        url=url,
        source="Test",
        published_at="2026-09-30T08:00:00+00:00",
        summary="summary",
    )


@pytest.fixture
def storage():
    storage = Storage(":memory:")
    yield storage
    storage.close()


@pytest.fixture
def fake_collect(monkeypatch):
    """Replace network collection with a fixed list of items."""
    items: list[NewsItem] = []
    monkeypatch.setattr(src.main, "collect_all", lambda max_item_hours: list(items))
    return items


class TestCollectCandidates:
    def test_skips_links_already_in_digest(self, storage, fake_collect) -> None:
        fake_collect.extend([_item("https://a.com/1"), _item("https://a.com/2")])
        storage.mark_link_sent("https://a.com/1")

        urls = [i.url for i in collect_candidates(storage, max_item_hours=72)]

        assert urls == ["https://a.com/2"]

    def test_drops_duplicate_urls_in_one_run(self, storage, fake_collect) -> None:
        fake_collect.extend(
            [_item("https://a.com/1", "HN"), _item("https://a.com/1", "Blog")]
        )

        items = collect_candidates(storage, max_item_hours=72)

        assert [i.title for i in items] == ["HN"]

    def test_second_run_does_not_repeat_marked_links(
        self, storage, fake_collect, tmp_path
    ) -> None:
        fake_collect.extend([_item("https://a.com/1"), _item("https://a.com/2")])
        digest = tmp_path / "2026-09-30.md"
        digest.write_text("## 1. Title\n\nTest, 30.09 - https://a.com/1\n")

        collect_candidates(storage, max_item_hours=72)
        mark_digest(storage, digest)
        second = collect_candidates(storage, max_item_hours=72)

        assert [i.url for i in second] == ["https://a.com/2"]


class TestMarkDigest:
    @pytest.mark.parametrize(
        "line",
        [
            "Source, 30.09 - https://a.com/post",
            "- Short line. https://a.com/post.",
            "Retelling (https://a.com/post)",
            "See <https://a.com/post>, then",
            "https://a.com/post;",
            "`https://a.com/post`",
            "«ссылка https://a.com/post»",
            'link "https://a.com/post"',
        ],
    )
    def test_marks_link_without_trailing_punctuation(
        self, storage, tmp_path, line
    ) -> None:
        digest = tmp_path / "digest.md"
        digest.write_text(f"# Digest\n\n{line}\n")

        mark_digest(storage, digest)

        assert storage.was_link_sent("https://a.com/post"), line

    def test_keeps_balanced_parenthesis_in_link(self, storage, tmp_path) -> None:
        digest = tmp_path / "digest.md"
        digest.write_text("- Wiki (https://en.wikipedia.org/wiki/Foo_(bar)).\n")

        mark_digest(storage, digest)

        assert storage.was_link_sent("https://en.wikipedia.org/wiki/Foo_(bar)")

    def test_marks_normalized_link(self, storage, tmp_path) -> None:
        digest = tmp_path / "digest.md"
        digest.write_text("https://habr.com/ru/articles/1/?utm_source=habrahabr\n")

        mark_digest(storage, digest)

        assert storage.was_link_sent("https://habr.com/ru/articles/1")

    def test_second_mark_of_same_file_is_harmless(self, storage, tmp_path) -> None:
        digest = tmp_path / "digest.md"
        digest.write_text("https://a.com/1\nhttps://a.com/2\n")

        assert mark_digest(storage, digest) == 2
        assert mark_digest(storage, digest) == 2


class TestCli:
    @pytest.fixture(autouse=True)
    def temp_db(self, monkeypatch, tmp_path):
        monkeypatch.setattr(src.main, "DB_PATH", tmp_path / "digest.db")

    def test_collect_prints_candidates_as_json(self, fake_collect, capsys) -> None:
        fake_collect.append(_item("https://a.com/1"))

        code = main(["collect"])

        assert code == 0
        printed = json.loads(capsys.readouterr().out)
        assert printed == [
            {
                "title": "Title",
                "url": "https://a.com/1",
                "source": "Test",
                "published_at": "2026-09-30T08:00:00+00:00",
                "summary": "summary",
                "score": 0.0,
            }
        ]

    def test_mark_missing_file_fails(self, tmp_path, capsys) -> None:
        code = main(["mark", str(tmp_path / "missing.md")])

        assert code == 1
        assert "missing.md" in capsys.readouterr().err
