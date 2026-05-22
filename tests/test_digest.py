from src.digest import build_digest, format_digest_message
from src.models import NewsItem


def _make_item(
    title: str = "Test",
    source: str = "OpenAI Blog",
    score: float = 3.0,
    why_it_matters: str = "Why it matters",
    action: str = "Read more",
    url: str = "https://example.com",
) -> NewsItem:
    return NewsItem(
        title=title,
        url=url,
        source=source,
        published_at="2025-01-01T00:00:00",
        summary="",
        score=score,
        why_it_matters=why_it_matters,
        action=action,
    )


class TestBuildDigest:
    def test_build_digest_basic(self) -> None:
        items = [
            _make_item(title="GPT-5", source="OpenAI Blog", score=5.0),
            _make_item(title="Codex CLI v2", source="OpenCode Releases", score=4.0),
            _make_item(title="Trending repo", source="GitHub Trending", score=3.0),
        ]
        result = build_digest(items)

        assert "🔥 Main Updates" in result
        assert "🧰 New Tools" in result
        assert "⭐ Trending" in result
        assert "1. GPT-5" in result
        assert "2. Codex CLI v2" in result
        assert "3. Trending repo" in result

    def test_build_digest_sorted_by_score(self) -> None:
        items = [
            _make_item(title="Low score", score=3.0),
            _make_item(title="High score", score=5.0),
        ]
        result = build_digest(items)

        high_index = result.find("High score")
        low_index = result.find("Low score")
        assert high_index < low_index

    def test_build_digest_empty(self) -> None:
        result = build_digest([])
        assert result == ""

    def test_build_digest_single_category(self) -> None:
        items = [
            _make_item(title="News A", source="OpenAI Blog"),
            _make_item(title="News B", source="Anthropic Blog"),
        ]
        result = build_digest(items)
        lines = result.strip().split("\n")

        assert lines[0] == "🔥 Main Updates"
        assert "🧰 New Tools" not in result

    def test_build_digest_sequential_index(self) -> None:
        items = [
            _make_item(title="A", source="OpenAI Blog", score=5.0),
            _make_item(title="B", source="OpenCode Releases", score=4.0),
            _make_item(title="C", source="GitHub Trending", score=3.0),
        ]
        result = build_digest(items)

        assert "1. A" in result
        assert "2. B" in result
        assert "3. C" in result


class TestFormatDigestMessage:
    def test_format_digest_message(self) -> None:
        items = [_make_item(title="GPT-5", source="OpenAI Blog", score=5.0)]
        result = format_digest_message(items)

        assert result.startswith("*🤖 AI Dev Digest*")
        assert result.endswith("---")
        assert "🔥 Main Updates" in result
        assert "1. GPT-5" in result

    def test_format_digest_message_empty(self) -> None:
        result = format_digest_message([])
        assert result == ""
