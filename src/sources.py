from dataclasses import dataclass


@dataclass
class SourceConfig:
    name: str
    url: str
    type: str


# Checks and reasons for each feed: docs/plans/claude-digest-sources.md
SOURCES: list[SourceConfig] = [
    SourceConfig("OpenAI Blog", "https://openai.com/blog/rss.xml", "rss"),
    SourceConfig(
        "Anthropic Blog",
        "https://raw.githubusercontent.com/taobojlen/anthropic-rss-feed/main/anthropic_news_rss.xml",
        "rss",
    ),
    SourceConfig(
        "Anthropic Engineering",
        "https://raw.githubusercontent.com/taobojlen/anthropic-rss-feed/main/anthropic_engineering_rss.xml",
        "rss",
    ),
    SourceConfig(
        "Cursor Blog",
        "https://raw.githubusercontent.com/leontloveless/ai-rss-feeds/main/feeds/cursor-blog.xml",
        "rss",
    ),
    SourceConfig("Google DeepMind", "https://deepmind.google/blog/rss.xml", "rss"),
    SourceConfig("Google AI", "https://blog.google/technology/ai/rss/", "rss"),
    SourceConfig("Hugging Face", "https://huggingface.co/blog/feed.xml", "rss"),
    SourceConfig("Simon Willison", "https://simonwillison.net/atom/everything/", "rss"),
    SourceConfig("Latent Space", "https://www.latent.space/feed", "rss"),
    SourceConfig(
        "Andrej Karpathy", "https://karpathy.bearblog.dev/feed/?type=rss", "rss"
    ),
    SourceConfig(
        "Andrej Karpathy (old blog)", "https://karpathy.github.io/feed.xml", "rss"
    ),
    SourceConfig(
        "Andrej Karpathy (YouTube)",
        "https://www.youtube.com/feeds/videos.xml?channel_id=UCXUPKJO5MZQN11PqgIvyuvQ",
        "rss",
    ),
    SourceConfig(
        "Habr AI",
        "https://habr.com/ru/rss/hubs/artificial_intelligence/articles/?fl=ru",
        "rss",
    ),
    # One combined feed: three separate Reddit requests in a row get 429
    SourceConfig(
        "Reddit", "https://www.reddit.com/r/ClaudeAI+OpenAI+LocalLLaMA/.rss", "rss"
    ),
    SourceConfig(
        "Hacker News",
        "https://hacker-news.firebaseio.com/v0/topstories.json",
        "hn_api",
    ),
    SourceConfig("GitHub Trending", "https://github.com/trending", "github_trending"),
]
