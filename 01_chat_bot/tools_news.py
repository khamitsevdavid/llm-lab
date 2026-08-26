import json
import feedparser
import requests

from config import MAX_NEWS, TIMEOUT


def get_news(topic="all", limit=5):
    feeds = {
        "python": "https://habr.com/ru/rss/hub/python/",
        "llm": "https://habr.com/ru/rss/hub/machine_learning/",
        "ai": "https://habr.com/ru/rss/hub/machine_learning/",
        "ml": "https://habr.com/ru/rss/hub/machine_learning/",
        "news": "https://lenta.ru/rss/news",
        "tech": "https://habr.com/ru/rss/hub/it_infrastructure/",
        "all": "https://habr.com/ru/rss/all/",
    }

    topic = str(topic).lower().strip()

    url = feeds.get(topic, feeds["all"])

    try:
        limit = int(limit)
    except (ValueError, TypeError):
        limit = 5

    limit = max(1, min(limit, MAX_NEWS))

    try:
        response = requests.get(url, timeout=TIMEOUT)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
    except requests.exceptions.RequestException:
        return "Не удалось получить новости из RSS."

    if not feed.entries:
        return "RSS-лента не содержит новостей."

    news = []

    for entry in feed.entries[:limit]:
        news.append(
            {
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
            }
        )

    return json.dumps(news, ensure_ascii=False)
