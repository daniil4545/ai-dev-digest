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
        url="https://raw.githubusercontent.com/taobojlen/anthropic-rss-feed/main/anthropic_news_rss.xml",
        type="rss",
        category="ai-news",
    ),
    SourceConfig(
        name="Cursor Blog",
        url="https://raw.githubusercontent.com/leontloveless/ai-rss-feeds/main/feeds/cursor-blog.xml",
        type="rss",
        category="tools",
    ),
    SourceConfig(
        name="Google DeepMind",
        url="https://raw.githubusercontent.com/leontloveless/ai-rss-feeds/main/feeds/deepmind-blog.xml",
        type="rss",
        category="ai-news",
    ),
    SourceConfig(
        name="Groq News",
        url="https://raw.githubusercontent.com/leontloveless/ai-rss-feeds/main/feeds/groq-news.xml",
        type="rss",
        category="ai-news",
    ),
    SourceConfig(
        name="Stability AI",
        url="https://raw.githubusercontent.com/leontloveless/ai-rss-feeds/main/feeds/stability-ai.xml",
        type="rss",
        category="ai-news",
    ),
    SourceConfig(
        name="Claude Code Changelog",
        url="https://github.com/anthropics/claude-code/releases.atom",
        type="rss",
        category="ai-news",
    ),
    SourceConfig(
        name="OpenCode Releases",
        url="https://github.com/anomalyco/opencode/releases.atom",
        type="rss",
        category="ai-news",
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
