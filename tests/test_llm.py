import json

import pytest

from src.config import Config
from src.llm import KEYWORDS, _extract_json, _heuristic_score, score_news, score_news_batch
from src.models import NewsItem


def _make_item(title: str = "Test", summary: str = "") -> NewsItem:
    return NewsItem(
        title=title,
        url="https://example.com",
        source="test",
        published_at="2025-01-01T00:00:00",
        summary=summary,
    )


def _mock_config(mocker):
    mocker.patch(
        "src.llm.get_config",
        return_value=Config(
            telegram_bot_token="test",
            telegram_chat_id="test",
            ollama_model="gemma3:4b",
            ollama_host="http://localhost:11434",
        ),
    )


def _mock_ollama_chat(mocker, return_value=None, side_effect=None):
    mock_client = mocker.Mock()
    if side_effect is not None:
        mock_client.chat.side_effect = side_effect
    else:
        mock_client.chat.return_value = return_value or {
            "message": {"content": '{"score": 3.0, "why_it_matters": "", "action": ""}'}
        }
    mocker.patch("src.llm.ollama.Client", return_value=mock_client)
    return mock_client


class TestExtractJson:
    def test_plain_json(self) -> None:
        data = _extract_json('{"score": 3}')
        assert data == {"score": 3}

    def test_inside_code_fence(self) -> None:
        data = _extract_json("```json\n{\"score\": 4}\n```")
        assert data == {"score": 4}

    def test_code_fence_without_lang(self) -> None:
        data = _extract_json("```\n{\"score\": 5}\n```")
        assert data == {"score": 5}

    def test_extra_text_before_json(self) -> None:
        data = _extract_json("Here is the JSON:\n{\"score\": 2}")
        assert data == {"score": 2}

    def test_extra_text_around_json(self) -> None:
        data = _extract_json("Rating: {\"score\": 1, \"why_it_matters\": \"ok\"}. End.")
        assert data == {"score": 1, "why_it_matters": "ok"}

    def test_unparseable_raises(self) -> None:
        with pytest.raises(json.JSONDecodeError):
            _extract_json("completely invalid")

    def test_trailing_comma_in_object(self) -> None:
        data = _extract_json('{"score": 4, "why": "test",}')
        assert data == {"score": 4, "why": "test"}

    def test_trailing_comma_in_array(self) -> None:
        data = _extract_json('[{"score": 3}, {"score": 4},]')
        assert len(data) == 2

    def test_trailing_comma_in_code_fence(self) -> None:
        data = _extract_json("```json\n{\"score\": 5,}\n```")
        assert data == {"score": 5}

    def test_single_quotes_no_double(self) -> None:
        data = _extract_json("{'score': 4, 'why': 'test'}")
        assert data == {"score": 4, "why": "test"}

    def test_single_quotes_in_code_fence(self) -> None:
        data = _extract_json("```json\n{'score': 3, 'why': 'ok'}\n```")
        assert data == {"score": 3, "why": "ok"}


class TestScoreNews:
    def test_score_news_success(self, mocker) -> None:
        _mock_config(mocker)
        _mock_ollama_chat(
            mocker,
            return_value={
                "message": {
                    "content": (
                        '{"score": 4.0, "summary": "Важное обновление платформы с новыми возможностями"}'
                    )
                }
            },
        )

        item = _make_item(title="New platform update", summary="New features")
        result = score_news([item])

        assert len(result) == 1
        assert result[0].score == 4.0
        assert result[0].why_it_matters == "Важное обновление платформы с новыми возможностями"

    def test_score_news_invalid_json(self, mocker) -> None:
        _mock_config(mocker)
        _mock_ollama_chat(
            mocker, return_value={"message": {"content": "not valid json"}}
        )

        item = _make_item()
        result = score_news([item])

        assert len(result) == 0

    def test_score_news_empty_json(self, mocker) -> None:
        _mock_config(mocker)
        _mock_ollama_chat(mocker, return_value={"message": {"content": "{}"}})

        item = _make_item()
        result = score_news([item])

        assert len(result) == 0

    def test_score_news_connection_error(self, mocker) -> None:
        _mock_config(mocker)
        _mock_ollama_chat(mocker, side_effect=RuntimeError("connection refused"))

        item = _make_item(title="Claude 4 release", summary="New model from Anthropic")
        result = score_news([item])

        assert len(result) == 1
        assert result[0].score == 3.0
        assert result[0].why_it_matters == "New model from Anthropic"

    def test_score_news_filter(self, mocker) -> None:
        _mock_config(mocker)
        mock_client = _mock_ollama_chat(mocker)
        mock_client.chat.side_effect = [
            {
                "message": {
                    "content": '{"score": 4.0, "why_it_matters": "A", "action": "B"}'
                }
            },
            {
                "message": {
                    "content": '{"score": 2.0, "why_it_matters": "C", "action": "D"}'
                }
            },
        ]

        items = [
            _make_item(title="Important news", summary="Great stuff"),
            _make_item(title="Boring news", summary="Meh"),
        ]
        result = score_news(items)

        assert len(result) == 1
        assert result[0].title == "Important news"
        assert result[0].score == 4.0


class TestHeuristicScore:
    def test_heuristic_score_high(self) -> None:
        item = _make_item(title="New Claude feature released")
        result = _heuristic_score(item)

        assert result.score == 3.0
        assert result.why_it_matters == "New Claude feature released"
        assert result.action == ""

    def test_heuristic_score_low(self) -> None:
        item = _make_item(title="Weather forecast for today")
        result = _heuristic_score(item)

        assert result.score == 1.0
        assert result.why_it_matters == ""
        assert result.action == ""

    def test_heuristic_score_keywords(self) -> None:
        for kw in sorted(KEYWORDS):
            item = _make_item(title=f"Great {kw} update")
            result = _heuristic_score(item)
            assert result.score == 3.0, f"Keyword '{kw}' not detected"

    def test_heuristic_score_summary(self) -> None:
        item = _make_item(title="Something", summary="This is about mcp protocol")
        result = _heuristic_score(item)

        assert result.score == 3.0

    def test_heuristic_score_case_insensitive(self) -> None:
        item = _make_item(title="CLAUDE Codex and GPT")
        result = _heuristic_score(item)

        assert result.score == 3.0


class TestScoreNewsBatch:
    def test_batch_success(self, mocker) -> None:
        _mock_config(mocker)
        _mock_ollama_chat(
            mocker,
            return_value={
                "message": {
                    "content": (
                        '[{"score": 4.0, "summary": "Big update"},'
                        ' {"score": 2.0, "summary": "Small update"}]'
                    )
                }
            },
        )

        items = [
            _make_item(title="Claude update", summary="New model"),
            _make_item(title="Random news", summary="Nothing special"),
        ]
        result = score_news_batch(items)

        assert len(result) == 1
        assert result[0].title == "Claude update"

    def test_batch_fallback_on_error(self, mocker) -> None:
        _mock_config(mocker)
        mock_client = _mock_ollama_chat(mocker)
        mock_client.chat.side_effect = RuntimeError("batch not supported")

        item = _make_item(title="New opencode release", summary="CLI tool update")
        result = score_news_batch([item])

        assert len(result) == 1
        assert result[0].score == 3.0

    def test_batch_invalid_response(self, mocker) -> None:
        _mock_config(mocker)
        mock_client = _mock_ollama_chat(mocker)
        mock_client.chat.side_effect = [
            {"message": {"content": "{}"}},
            ConnectionError("timeout"),
        ]

        item = _make_item(title="Claude", summary="")
        result = score_news_batch([item])

        assert len(result) == 1
        assert result[0].score == 3.0
