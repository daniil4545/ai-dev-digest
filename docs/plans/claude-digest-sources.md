# Источники дайджеста

Приложение к [claude-digest.md](claude-digest.md). Каждая лента проверена живым запросом 30.09.2026 с User-Agent сборщика: код ответа 200, число постов за 30 дней.

## Итоговый список

| Источник | Тип | URL | Постов за 30 дней |
|---|---|---|---|
| OpenAI Blog | rss | https://openai.com/blog/rss.xml | 8 за 72 ч |
| Anthropic Blog | rss, неофициальная | https://raw.githubusercontent.com/taobojlen/anthropic-rss-feed/main/anthropic_news_rss.xml | 1 за 72 ч |
| Anthropic Engineering | rss, неофициальная | https://raw.githubusercontent.com/taobojlen/anthropic-rss-feed/main/anthropic_engineering_rss.xml | 1 |
| Cursor Blog | rss, неофициальная | https://raw.githubusercontent.com/leontloveless/ai-rss-feeds/main/feeds/cursor-blog.xml | последний 23.09 |
| Google DeepMind | rss | https://deepmind.google/blog/rss.xml | 9 |
| Google AI | rss | https://blog.google/technology/ai/rss/ | 17 |
| Hugging Face | rss | https://huggingface.co/blog/feed.xml | 17 |
| Simon Willison | rss (Atom) | https://simonwillison.net/atom/everything/ | 30 |
| Latent Space | rss | https://www.latent.space/feed | 20 |
| Andrej Karpathy, блог | rss | https://karpathy.bearblog.dev/feed/?type=rss | последний 30.04 |
| Andrej Karpathy, старый блог | rss | https://karpathy.github.io/feed.xml | последний 12.02 |
| Andrej Karpathy, YouTube | rss (Atom) | https://www.youtube.com/feeds/videos.xml?channel_id=UCXUPKJO5MZQN11PqgIvyuvQ | последний 27.02.2025 |
| Habr, хаб AI | rss | https://habr.com/ru/rss/hubs/artificial_intelligence/articles/?fl=ru | 40 за 72 ч |
| Reddit ClaudeAI, OpenAI, LocalLLaMA | rss (Atom), одна лента | https://www.reddit.com/r/ClaudeAI+OpenAI+LocalLLaMA/.rss | 25 за 72 ч |
| Hacker News | hn_api | https://hacker-news.firebaseio.com/v0/topstories.json | 30 за 72 ч |
| GitHub Trending | github_trending | https://github.com/trending | 14 |

## Убраны

- Groq News, Stability AI: последние посты 22.06 и 25.08
- Claude Code и OpenCode releases: заголовки из номеров версий, в тестовый выпуск не попал ни один
- Google DeepMind, неофициальная копия: не обновлялась с 01.09, заменена официальной лентой
- Reddit JSON API по трём сабам: 403; три RSS-запроса подряд дают 429

## Проверены и не взяты

- Google Developers: у записей нет даты, со сборщиком каждая была бы «сегодня»
- Meta AI: официальной RSS не нашлось (`ai.meta.com/blog/rss/` и `/feed/` отдают 404), неофициальная копия остановилась 27.07; Meta Engineering слишком широкий
- Ollama blog (1 пост за 30 дней), Ollama releases (номера версий), Sebastian Raschka (2), Hamel Husain (1): по решению владельца не взяты
- Chip Huyen, Eugene Yan: последние посты 16.01.2025 и 21.06.2026

## Ограничения

- Неофициальные ленты на GitHub могут остановиться, как копия Meta AI
- openai.com отдаёт WebFetch 403: разбор идёт по пересказу из других кандидатов
- У видео YouTube и выпусков подкаста Latent Space WebFetch видит только описание
