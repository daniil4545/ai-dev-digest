from dataclasses import dataclass


@dataclass
class SourceConfig:
    name: str
    url: str
    type: str
    category: str


SOURCES: list[SourceConfig] = [
    SourceConfig(
        name="OpenAI Blog",
        url="https://openai.com/blog/rss.xml",
        type="rss",
        category="ai-news",
    ),
    SourceConfig(
        name="Anthropic Blog",
        url="https://www.anthropic.com/rss.xml",
        type="rss",
        category="ai-news",
    ),
    SourceConfig(
        name="Claude Code Changelog",
        url="https://github.com/anthropics/claude-code/releases.atom",
        type="rss",
        category="tools",
    ),
    SourceConfig(
        name="OpenCode Releases",
        url="https://github.com/anomalyco/opencode/releases.atom",
        type="rss",
        category="tools",
    ),
    SourceConfig(
        name="GitHub Trending",
        url="https://github.com/trending",
        type="github_trending",
        category="trending",
    ),
    SourceConfig(
        name="Hacker News",
        url="https://hacker-news.firebaseio.com/v0/topstories.json",
        type="hn_api",
        category="dev-news",
    ),
    SourceConfig(
        name="Reddit r/ClaudeAI",
        url="https://www.reddit.com/r/ClaudeAI/hot.json",
        type="reddit_api",
        category="community",
    ),
    SourceConfig(
        name="Reddit r/OpenAI",
        url="https://www.reddit.com/r/OpenAI/hot.json",
        type="reddit_api",
        category="community",
    ),
    SourceConfig(
        name="Reddit r/LocalLLaMA",
        url="https://www.reddit.com/r/LocalLLaMA/hot.json",
        type="reddit_api",
        category="community",
    ),
]
