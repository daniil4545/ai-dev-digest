from dataclasses import dataclass


@dataclass
class NewsItem:
    title: str
    url: str
    source: str
    published_at: str
    summary: str
    score: float = 0.0  # popularity at the source: HN points, GitHub stars; 0 for RSS
