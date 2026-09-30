import time
from datetime import UTC, datetime

import pytest
import requests

from src.collect import (
    _filter_recent,
    _parse_date,
    _truncate,
    collect_all,
    fetch_github_trending,
    fetch_hn_top,
    fetch_rss,
    normalize_url,
)
from src.models import NewsItem
from src.sources import SOURCES


class TestHelpers:
    def test_truncate_short(self) -> None:
        assert _truncate("hello") == "hello"

    def test_truncate_long(self) -> None:
        text = "a " * 500
        result = _truncate(text)
        assert len(result) <= 503
        assert result.endswith("...")

    def test_parse_date_none(self) -> None:
        result = _parse_date(None)
        assert result.endswith("+00:00") or result.endswith("Z") or "T" in result

    def test_parse_date_valid(self) -> None:
        result = _parse_date((2025, 6, 1, 12, 0, 0, 6, 152, 0))
        assert result == "2025-06-01T12:00:00+00:00"


class TestFilterRecent:
    def _item(self, published_at: str) -> NewsItem:
        return NewsItem(
            title="Test",
            url="https://example.com",
            source="test",
            published_at=published_at,
            summary="",
        )

    def test_recent_item_passes(self) -> None:
        now = datetime.now(UTC).isoformat()
        items = [self._item(now)]
        result = _filter_recent(items, hours=24)
        assert len(result) == 1

    def test_old_item_filtered(self) -> None:
        items = [self._item("2024-01-01T00:00:00+00:00")]
        result = _filter_recent(items, hours=24)
        assert len(result) == 0

    def test_mixed_items(self) -> None:
        now = datetime.now(UTC).isoformat()
        items = [
            self._item("2024-01-01T00:00:00+00:00"),
            self._item(now),
        ]
        result = _filter_recent(items, hours=24)
        assert len(result) == 1

    def test_invalid_date_passes(self) -> None:
        items = [self._item("not-a-date")]
        result = _filter_recent(items, hours=24)
        assert len(result) == 1

    def test_empty_list(self) -> None:
        result = _filter_recent([], hours=24)
        assert result == []


class TestFetchRSS:
    def test_fetch_rss(self, mocker) -> None:
        mock_get = mocker.patch("src.collect.requests.get")
        mock_get.return_value.text = (
            "<rss><channel><item><title>dummy</title></item></channel></rss>"
        )
        mock_parse = mocker.patch("src.collect.feedparser.parse")

        class MockEntry:
            title = "RSS Article"
            link = "https://example.com/article"
            summary = "Article summary text"

            def get(self, key, default=None):
                if key == "published_parsed":
                    return time.struct_time((2025, 1, 1, 0, 0, 0, 2, 1, 0))
                return default

        mock_feed = mocker.Mock()
        mock_feed.entries = [MockEntry()]
        mock_parse.return_value = mock_feed

        items = fetch_rss("https://example.com/rss")
        assert len(items) == 1
        assert items[0].title == "RSS Article"
        assert items[0].url == "https://example.com/article"
        assert items[0].summary == "Article summary text"

    def test_fetch_rss_no_date(self, mocker) -> None:
        mock_get = mocker.patch("src.collect.requests.get")
        mock_get.return_value.text = (
            "<rss><channel><item><title>dummy</title></item></channel></rss>"
        )
        mock_parse = mocker.patch("src.collect.feedparser.parse")

        class MockEntry:
            title = "No Date"
            link = "https://example.com/2"
            summary = ""

            def get(self, key, default=None):
                if key == "published_parsed":
                    return None
                return default

        mock_feed = mocker.Mock()
        mock_feed.entries = [MockEntry()]
        mock_parse.return_value = mock_feed

        items = fetch_rss("https://example.com/rss")
        assert len(items) == 1
        assert "T" in items[0].published_at


class TestFetchHN:
    def test_fetch_hn_top(self, mocker) -> None:
        mock_get = mocker.patch("src.collect.requests.get")

        list_resp = mocker.Mock()
        list_resp.json.return_value = [1, 2]
        list_resp.raise_for_status.return_value = None

        def make_item_resp(item_id: int):
            resp = mocker.Mock()
            resp.json.return_value = {
                "title": f"Story {item_id}",
                "url": f"https://example.com/{item_id}",
                "score": 42,
                "time": 1700000000,
            }
            resp.raise_for_status.return_value = None
            return resp

        mock_get.side_effect = [list_resp, make_item_resp(1), make_item_resp(2)]

        items = fetch_hn_top()
        assert len(items) == 2
        assert items[0].title == "Story 1"
        assert items[0].score == 42.0
        assert items[0].url == "https://example.com/1"

    def test_fetch_hn_missing_url(self, mocker) -> None:
        mock_get = mocker.patch("src.collect.requests.get")

        list_resp = mocker.Mock()
        list_resp.json.return_value = [99]
        list_resp.raise_for_status.return_value = None

        item_resp = mocker.Mock()
        item_resp.json.return_value = {
            "title": "Ask HN: Question?",
            "score": 10,
            "time": 1700000000,
        }
        item_resp.raise_for_status.return_value = None

        mock_get.side_effect = [list_resp, item_resp]

        items = fetch_hn_top()
        assert len(items) == 1
        assert items[0].title == "Ask HN: Question?"
        assert "news.ycombinator.com" in items[0].url

    def test_fetch_hn_no_title(self, mocker) -> None:
        mock_get = mocker.patch("src.collect.requests.get")

        list_resp = mocker.Mock()
        list_resp.json.return_value = [1]
        list_resp.raise_for_status.return_value = None

        item_resp = mocker.Mock()
        item_resp.json.return_value = {"deleted": True}
        item_resp.raise_for_status.return_value = None

        mock_get.side_effect = [list_resp, item_resp]

        items = fetch_hn_top()
        assert len(items) == 0


class TestFetchGitHubTrending:
    def test_fetch_github_trending(self, mocker) -> None:
        mock_get = mocker.patch("src.collect.requests.get")

        html = """
        <html><body>
        <article class="Box-row">
          <h2><a href="/owner/repo">owner/repo</a></h2>
          <p>Description of the repository</p>
          <a class="Link--muted">1,234</a>
        </article>
        <article class="Box-row">
          <h2><a href="/user/another-repo">user/another-repo</a></h2>
          <p>Another description</p>
          <a class="Link--muted">567</a>
        </article>
        </body></html>
        """

        resp = mocker.Mock()
        resp.text = html
        resp.raise_for_status.return_value = None
        mock_get.return_value = resp

        items = fetch_github_trending("https://github.com/trending")
        assert len(items) == 2
        assert items[0].title == "owner/repo"
        assert items[0].url == "https://github.com/owner/repo"
        assert items[0].summary == "Description of the repository"
        assert items[0].score == 1234.0
        assert items[1].title == "user/another-repo"

    def test_fetch_github_trending_no_stars(self, mocker) -> None:
        mock_get = mocker.patch("src.collect.requests.get")

        html = """
        <html><body>
        <article class="Box-row">
          <h2><a href="/owner/repo">owner/repo</a></h2>
          <p>Description</p>
        </article>
        </body></html>
        """

        resp = mocker.Mock()
        resp.text = html
        resp.raise_for_status.return_value = None
        mock_get.return_value = resp

        items = fetch_github_trending("https://github.com/trending")
        assert len(items) == 1
        assert items[0].score == 0.0


class TestCollectAll:
    def test_collect_all_empty_sources(self, mocker) -> None:
        mock_fetch = mocker.Mock(return_value=[])
        mocker.patch("src.collect.SOURCES", [])
        mocker.patch.dict("src.collect.FETCH_MAP", {"rss": mock_fetch}, clear=True)

        assert collect_all() == []
        mock_fetch.assert_not_called()

    def test_collect_all(self, mocker) -> None:
        rss_item = NewsItem(
            title="RSS Item",
            url="https://example.com",
            source="",
            published_at="2025-01-01T00:00:00",
            summary="",
        )
        hn_item = NewsItem(
            title="HN Item",
            url="https://news.ycombinator.com/item?id=1",
            source="",
            published_at="2025-01-01T00:00:00",
            summary="",
        )

        mock_fetch_rss = mocker.Mock(return_value=[rss_item])
        mock_fetch_hn = mocker.Mock(return_value=[hn_item])
        mock_fetch_gh = mocker.Mock(return_value=[])

        mocker.patch.dict(
            "src.collect.FETCH_MAP",
            {
                "rss": mock_fetch_rss,
                "hn_api": mock_fetch_hn,
                "github_trending": mock_fetch_gh,
            },
            clear=True,
        )
        mocker.patch("src.collect._filter_recent", side_effect=lambda x, **kw: x)

        items = collect_all()

        rss_source_count = sum(1 for s in SOURCES if s.type == "rss")
        hn_source_count = sum(1 for s in SOURCES if s.type == "hn_api")
        gh_source_count = sum(1 for s in SOURCES if s.type == "github_trending")

        assert mock_fetch_rss.call_count == rss_source_count
        assert mock_fetch_hn.call_count == hn_source_count
        assert mock_fetch_gh.call_count == gh_source_count

        assert len(items) == rss_source_count + hn_source_count
        for item in items:
            assert item.source != ""


class TestErrorHandling:
    def test_fetch_error_handling(self, mocker) -> None:
        mock_get = mocker.patch("src.collect.requests.get")
        mock_get.side_effect = requests.ConnectionError("connection failed")

        items = fetch_github_trending("https://github.com/trending")
        assert items == []

    def test_collect_all_continues_on_error(self, mocker) -> None:
        mock_get = mocker.patch("src.collect.requests.get")
        mock_get.side_effect = requests.ConnectionError("connection failed")

        items = collect_all()
        assert items == []

    def test_fetch_hn_skips_bad_item_json(self, mocker) -> None:
        mock_get = mocker.patch("src.collect.requests.get")

        list_resp = mocker.Mock()
        list_resp.json.return_value = [1, 2]
        list_resp.raise_for_status.return_value = None

        bad_resp = mocker.Mock()
        bad_resp.json.side_effect = ValueError("bad json")
        bad_resp.raise_for_status.return_value = None

        good_resp = mocker.Mock()
        good_resp.json.return_value = {
            "title": "Good Story",
            "url": "https://example.com/good",
            "score": 10,
            "time": 1700000000,
        }
        good_resp.raise_for_status.return_value = None

        mock_get.side_effect = [list_resp, bad_resp, good_resp]

        items = fetch_hn_top()

        assert len(items) == 1
        assert items[0].title == "Good Story"


class TestSources:
    def test_source_has_required_fields(self) -> None:
        for source in SOURCES:
            assert source.name, f"Source missing name: {source}"
            assert source.url, f"Source {source.name} missing url"
            assert source.type in (
                "rss",
                "hn_api",
                "github_trending",
            ), f"Source {source.name} has unknown type: {source.type}"

    def test_sources_count(self) -> None:
        assert len(SOURCES) >= 9

    def test_source_name_unique(self) -> None:
        names = [s.name for s in SOURCES]
        assert len(names) == len(set(names)), f"Duplicate names: {names}"


class TestNormalizeUrl:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("https://openai.com/index/dots/", "https://openai.com/index/dots"),
            ("https://openai.com/index/dots", "https://openai.com/index/dots"),
            (
                "https://habr.com/ru/articles/1/?utm_campaign=1&utm_source=habrahabr",
                "https://habr.com/ru/articles/1",
            ),
            (
                "https://news.ycombinator.com/item?id=1&utm_medium=rss",
                "https://news.ycombinator.com/item?id=1",
            ),
            ("https://example.com/", "https://example.com"),
            ("HTTPS://Example.COM/Path", "https://example.com/Path"),
        ],
    )
    def test_normalize_url(self, raw: str, expected: str) -> None:
        assert normalize_url(raw) == expected


ATOM_FEED = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Releases</title>
  <entry>
    <title>Atom entry</title>
    <link href="https://example.com/entry"/>
    <updated>2026-09-29T10:00:00Z</updated>
    <content type="html">&lt;p&gt;First &lt;b&gt;bold&lt;/b&gt; line&lt;/p&gt;</content>
  </entry>
</feed>
"""


class TestFetchAtom:
    def test_atom_entry_uses_updated_date_and_plain_summary(self, mocker) -> None:
        response = mocker.Mock(text=ATOM_FEED)
        mocker.patch("src.collect.requests.get", return_value=response)

        items = fetch_rss("https://example.com/feed.atom")

        assert len(items) == 1
        assert items[0].published_at == "2026-09-29T10:00:00+00:00"
        assert items[0].summary == "First bold line"


class TestTrendingTitle:
    def test_title_without_line_breaks(self, mocker) -> None:
        html = """
        <article class="Box-row">
          <h2><a href="/NVIDIA/OpenShell">NVIDIA /

          OpenShell</a></h2>
        </article>
        """
        response = mocker.Mock(text=html)
        mocker.patch("src.collect.requests.get", return_value=response)

        items = fetch_github_trending("https://github.com/trending")

        assert items[0].title == "NVIDIA/OpenShell"


class TestCollectAllNormalizes:
    def test_urls_are_normalized(self, mocker) -> None:
        item = NewsItem(
            title="Post",
            url="https://habr.com/ru/articles/1/?utm_source=habrahabr",
            source="",
            published_at=datetime.now(UTC).isoformat(),
            summary="",
        )
        rss_sources = [s for s in SOURCES if s.type == "rss"]
        mocker.patch("src.collect.SOURCES", rss_sources[:1])
        mocker.patch.dict(
            "src.collect.FETCH_MAP", {"rss": lambda url: [item]}, clear=True
        )

        items = collect_all()

        assert items[0].url == "https://habr.com/ru/articles/1"
