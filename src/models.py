from dataclasses import dataclass


@dataclass
class NewsItem:
    title: str
    url: str
    source: str
    published_at: str
    summary: str
    score: float = 0.0
    why_it_matters: str = ""
    action: str = ""
