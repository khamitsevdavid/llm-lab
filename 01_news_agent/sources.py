import feedparser
import requests
from bs4 import BeautifulSoup
from typing import Any

primary = {  # чем проверяем
    "frontier_research": "https://rss.arxiv.org/rss/cs.AI+cs.LG+cs.CL",  # уже включает cs.CL
    "arxiv_cs_cr": "https://rss.arxiv.org/rss/cs.CR",
    "ai_safety": "https://newsletter.safe.ai/feed",
    "bair": "https://bair.berkeley.edu/blog/feed.xml",
    "google_research": "https://research.google/blog/rss/",
}

laboratories = {
    "deepmind": "https://deepmind.google/blog/rss.xml",
    "microsoft_research": "https://www.microsoft.com/en-us/research/feed/",
    "ibm_research": "https://research.ibm.com/rss",
    "apple_ml_research": "https://machinelearning.apple.com/rss.xml",
    "nvidia_developer": "https://developer.nvidia.com/blog/feed/",
    "ai2": "https://raw.githubusercontent.com/alan-turing-institute/ai-rss-feeds/main/feeds/allenai-news.xml",
    "aisi": "https://raw.githubusercontent.com/alan-turing-institute/ai-rss-feeds/main/feeds/aisi-blog.xml",
    "cohere": "https://raw.githubusercontent.com/alan-turing-institute/ai-rss-feeds/main/feeds/cohere-blog.xml",
    "mistral": "https://raw.githubusercontent.com/alan-turing-institute/ai-rss-feeds/main/feeds/mistral-news.xml",
    # unofficial
    "anthropic_research": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_research.xml",
}

universities = {
    # russian research universities
    "hse_science": "https://www.hse.ru/rss/rss_news_science.rss",
    # world top research universities
    "mit_ai": "https://news.mit.edu/rss/topic/artificial-intelligence2",
    "cmu_cs": "https://csd.cmu.edu/news.rss",
    "harvard_science_technology": "https://news.harvard.edu/gazette/section/science-technology/feed/",
    "uw_research": "https://www.washington.edu/news/category/research/feed/",
    "uw_science": "https://www.washington.edu/news/category/science/feed/",
}

SOURCES = {
    "primary": primary,
    "laboratories": laboratories,
    "universities": universities,
}


# ---helpers---


def clean_html(html: str) -> str:
    """HTML -> чистый текст. removesuffix убирает фразу целиком (rstrip убирал бы буквы)."""
    text = BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True)
    return text.removesuffix("Читать далее").strip()


def entries_to_items(entries: list, theme: str, limit: int = 30) -> list[dict[str, Any]]:
    """Записи feedparser -> наши словари (те же поля, что у NewsItem)."""
    items = []
    for ent in entries[:limit]:
        link = ent.get("link")
        title = ent.get("title")
        if not link or not title:  # без заголовка или ссылки запись бесполезна
            continue
        items.append(
            {
                "id": ent.get("id") or link,  # если у записи нет id — берём ссылку
                "theme": theme,  # для первоисточников тут имя ленты ("bair", ...)
                "title": title,
                "link": link,
                "summary": clean_html(ent.get("summary", "")),
            }
        )
    return items


def load_primary(limit: int = 30) -> list[dict[str, Any]]:
    """Скачивает все ленты из SOURCES['primary'] (до limit записей с каждой)."""
    items = []
    for name, url in SOURCES["primary"].items():
        try:
            r = requests.get(url, timeout=30, headers={"User-Agent": "news_agent_v2/0.1"})
            r.raise_for_status()
            feed = feedparser.parse(r.content)
        except requests.exceptions.RequestException as e:
            print(f"[primary] {name}: {type(e).__name__}")
            continue
        got = entries_to_items(feed.entries, name, limit)
        # bozo=True значит, что XML был битый; полезно для диагностики пустых лент
        print(f"[primary] {name}: {len(got)} записей (bozo={feed.bozo})")
        items += got
    return items


if __name__ == "__main__":
    # диагностика: python sources.py  — покажет, какие ленты пустые и почему
    load_primary()
