import time

import requests

from src.collect import (
    _parse_date,
    _truncate,
    collect_all,
    fetch_github_trending,
    fetch_hn_top,
    fetch_reddit_hot,
    fetch_rss,
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


class TestFetchRSS:
    def test_fetch_rss(self, mocker) -> None:
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


class TestFetchReddit:
    def test_fetch_reddit_hot(self, mocker) -> None:
        mock_get = mocker.patch("src.collect.requests.get")

        resp = mocker.Mock()
        resp.json.return_value = {
            "data": {
                "children": [
                    {
                        "data": {
                            "title": "Reddit Post",
                            "url": "https://example.com/reddit",
                            "score": 100,
                            "created_utc": 1700000000,
                        }
                    }
                ]
            }
        }
        resp.raise_for_status.return_value = None
        mock_get.return_value = resp

        items = fetch_reddit_hot("https://www.reddit.com/r/test/hot.json")
        assert len(items) == 1
        assert items[0].title == "Reddit Post"
        assert items[0].score == 100.0

    def test_fetch_reddit_self_post(self, mocker) -> None:
        mock_get = mocker.patch("src.collect.requests.get")

        resp = mocker.Mock()
        resp.json.return_value = {
            "data": {
                "children": [
                    {
                        "data": {
                            "title": "Self Post",
                            "url": "https://www.reddit.com/r/test/comments/abc/self_post/",
                            "permalink": "/r/test/comments/abc/self_post/",
                            "score": 50,
                            "created_utc": 1700000000,
                            "selftext": "Self text content",
                        }
                    }
                ]
            }
        }
        resp.raise_for_status.return_value = None
        mock_get.return_value = resp

        items = fetch_reddit_hot("https://www.reddit.com/r/test/hot.json")
        assert len(items) == 1
        assert "reddit.com" in items[0].url

    def test_fetch_reddit_no_url(self, mocker) -> None:
        mock_get = mocker.patch("src.collect.requests.get")

        resp = mocker.Mock()
        resp.json.return_value = {
            "data": {
                "children": [
                    {
                        "data": {
                            "title": "No URL Post",
                            "url": "",
                            "permalink": "/r/test/comments/xyz/no_url/",
                            "score": 10,
                            "created_utc": 1700000000,
                        }
                    }
                ]
            }
        }
        resp.raise_for_status.return_value = None
        mock_get.return_value = resp

        items = fetch_reddit_hot("https://www.reddit.com/r/test/hot.json")
        assert len(items) == 1
        assert "reddit.com" in items[0].url


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
        mock_fetch_reddit = mocker.Mock(return_value=[])
        mock_fetch_gh = mocker.Mock(return_value=[])

        mocker.patch.dict(
            "src.collect.FETCH_MAP",
            {
                "rss": mock_fetch_rss,
                "hn_api": mock_fetch_hn,
                "reddit_api": mock_fetch_reddit,
                "github_trending": mock_fetch_gh,
            },
        )

        items = collect_all()

        rss_source_count = sum(1 for s in SOURCES if s.type == "rss")
        hn_source_count = sum(1 for s in SOURCES if s.type == "hn_api")
        reddit_source_count = sum(1 for s in SOURCES if s.type == "reddit_api")
        gh_source_count = sum(1 for s in SOURCES if s.type == "github_trending")

        assert mock_fetch_rss.call_count == rss_source_count
        assert mock_fetch_hn.call_count == hn_source_count
        assert mock_fetch_reddit.call_count == reddit_source_count
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


class TestSources:
    def test_source_has_required_fields(self) -> None:
        for source in SOURCES:
            assert source.name, f"Source missing name: {source}"
            assert source.url, f"Source {source.name} missing url"
            assert source.type in (
                "rss",
                "hn_api",
                "reddit_api",
                "github_trending",
            ), f"Source {source.name} has unknown type: {source.type}"

    def test_sources_count(self) -> None:
        assert len(SOURCES) == 9

    def test_source_name_unique(self) -> None:
        names = [s.name for s in SOURCES]
        assert len(names) == len(set(names)), f"Duplicate names: {names}"
