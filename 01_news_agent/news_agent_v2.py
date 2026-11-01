# imports
import requests
import json
from typing import Any
import datetime
import feedparser
from pydantic import BaseModel, ValidationError
import chromadb
from chromadb.api.models.Collection import Collection

from sources import load_primary, clean_html

# ---constants---

with open("system_message.txt", encoding="UTF-8") as file:
    system_message = file.read()

OLLAMA = "http://localhost:11434/api/"
TIMEOUT = 90
CHAT_MODEL = "qwen2.5:7b"
EMBED_MODEL = "bge-m3:latest"
MAX_TURNS = 10
MAX_STEPS = 4
CANDIDATES = 3
SYSTEM_MESSAGE = {"role": "system", "content": system_message}

HABR_FEEDS = {
    "artificial_intelligence": "https://habr.com/ru/rss/hubs/artificial_intelligence/articles/?fl=ru",
    "machine_learning": "https://habr.com/ru/rss/hubs/machine_learning/articles/?fl=ru",
    "cybersecurity": "https://habr.com/ru/rss/hubs/infosecurity/articles/?fl=ru",
    "top": "https://habr.com/ru/rss/best/daily/?fl=ru",
}

# ---hystory---
history = [SYSTEM_MESSAGE]


def cut_history(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    conversation = history[1:]

    # by "user"
    choose_turns = [i for i, msg in enumerate(conversation) if msg["role"] == "user"]

    if len(choose_turns) <= MAX_TURNS:
        return history.copy()

    start_position = choose_turns[-MAX_TURNS]
    return history[:1] + conversation[start_position:]


# ---NewsItem---


class NewsItem(BaseModel):
    id: str
    theme: str
    title: str
    link: str
    summary: str | None = None
    published: str | None = None


# ---Embeddings---
# get embeddings (пачками по 32, чтобы не упереться в TIMEOUT на больших лентах)
def embed_texts(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    result = []
    for i in range(0, len(texts), batch_size):
        payload = {"model": EMBED_MODEL, "input": texts[i : i + batch_size]}
        r = requests.post(f"{OLLAMA}embed", json=payload, timeout=TIMEOUT)
        r.raise_for_status()
        result += r.json()["embeddings"]
    return result


# ---Collections---

client = chromadb.Client()


def make_collection(name: str) -> Collection:
    return client.get_or_create_collection(
        name, configuration={"hnsw": {"space": "cosine"}}
    )


habr_collection = make_collection("habr_news")
primary_collection = make_collection("primary_news")


def fill_collection(collection: Collection, items: list[dict[str, Any]]) -> None:
    unique = list({n["id"]: n for n in items}.values())
    if unique:
        old = set(collection.get(ids=[n["id"] for n in unique])["ids"])
    if not unique:
        return
        unique = [
            n for n in unique if n["id"] not in old
        ]  # уже сохранённые не пересчитываем
    docs = [n["title"] + " " + (n["summary"] or "") for n in unique]
    collection.upsert(
        ids=[n["id"] for n in unique],
        documents=docs,
        embeddings=embed_texts(docs),
        metadatas=[
            {"theme": n["theme"], "title": n["title"], "link": n["link"]}
            for n in unique
        ],
    )


# ---Exceptions---


def handle_exception(e: Exception, category: str) -> None:
    if category == "requests":
        if isinstance(e, requests.exceptions.ConnectionError):
            print("Connection error [u]")
        elif isinstance(e, requests.exceptions.HTTPError):
            print("Http error [u]")
        elif isinstance(e, requests.exceptions.Timeout):
            print("timeout [u]")
        else:
            print(type(e).__name__, e, "[sys]")

    elif category == "pydantic":
        print(type(e).__name__, e)


# ---tools description---


def tools_description() -> list[dict]:
    tools_list = []
    tool_time = {
        "type": "function",
        "function": {
            "name": "tool_time",
            "description": "Получает текущие время и дату",
            "parameters": {"type": "object", "properties": {}},
        },
    }
    tools_list.append(tool_time)
    tool_news = {
        "type": "function",
        "function": {
            "name": "tool_news",
            "description": "Показывает свежие новости из RSS Хабра по теме (заголовки и ссылки)",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Категория новостей",
                        "enum": list(HABR_FEEDS),
                    }
                },
                "required": ["topic"],
            },
        },
    }
    tools_list.append(tool_news)

    tool_search_news = {
        "type": "function",
        "function": {
            "name": "tool_search_news",
            "description": (
                "Семантический поиск по смыслу вопроса: находит статьи Хабра "
                "и для каждой — первоисточник (arXiv, BAIR, Google Research и др.). "
                "Используй для вопросов про исследования и конкретные темы. "
                "Нужные статьи загружает сам."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Поисковый запрос на русском, переформулированный из вопроса пользователя",
                    }
                },
                "required": ["query"],
            },
        },
    }
    tools_list.append(tool_search_news)

    return tools_list


TOOL_NAMES = [t["function"]["name"] for t in tools_description()]


# ---send promt for LLM---


def get_response(messages: list[dict[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": CHAT_MODEL,
        "messages": messages,
        "tools": tools_description(),
        "stream": False,
    }

    resp = requests.post(f"{OLLAMA}chat", json=payload, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


# ---tools---


def load_habr(topic: str) -> list[dict[str, Any]]:
    news = []
    try:
        r = requests.get(HABR_FEEDS[topic], timeout=TIMEOUT)
        r.raise_for_status()
        raw_news = feedparser.parse(r.content)
        for ent in raw_news.entries[:10]:
            try:
                ent["summary"] = clean_html(ent.get("summary", ""))
                news.append(NewsItem(theme=topic, **ent).model_dump())
            except ValidationError as e:
                handle_exception(e, "pydantic")
    except Exception as e:
        handle_exception(e, "requests")
    return news


def tool_news(topic: str = "top", collection: Collection = habr_collection) -> str:
    if topic not in HABR_FEEDS:
        return "Передана некорректная новостная тема."
    news = load_habr(topic)
    fill_collection(collection, news)
    short = [
        {"title": n["title"], "link": n["link"], "summary": (n["summary"] or "")[:200]}
        for n in news
    ]
    return json.dumps(short, ensure_ascii=False)


def tool_search_news(
    query: str,
    collection: Collection = habr_collection,
    primary: Collection = primary_collection,
) -> str:
    # 1. нет статей -> сначала tool_news; нет первоисточников -> качаем их
    if collection.count() == 0:
        for topic in ("artificial_intelligence", "machine_learning"):
            tool_news(topic, collection)
    if primary.count() == 0:
        fill_collection(primary, load_primary())
    if collection.count() == 0 or primary.count() == 0:
        return "Не удалось загрузить статьи или первоисточники."

    # 2. статьи Хабра, близкие к вопросу (+ их векторы, чтобы не считать заново)
    found = collection.query(
        query_embeddings=embed_texts([query]),
        n_results=min(CANDIDATES, collection.count()),
        include=["metadatas", "embeddings", "distances"],
    )
    metas = found["metadatas"][0]

    # 3. для каждой статьи — ближайшая запись первоисточника (одним запросом)
    nearest = primary.query(
        query_embeddings=found["embeddings"][0],
        n_results=1,
        include=["metadatas", "distances"],
    )

    # 4. собираем результат; distance у cosine = 1 - сходство
    rows = []
    for meta, src_metas, src_dists in zip(
        metas, nearest["metadatas"], nearest["distances"]
    ):
        src = src_metas[0]
        rows.append(
            {
                "title": meta["title"],
                "link": meta["link"],
                "primary_source": src["theme"],
                "primary_title": src["title"],
                "primary_link": src["link"],
                "similarity": round(1 - src_dists[0], 2),
            }
        )
    rows.sort(key=lambda row: row["similarity"], reverse=True)
    return json.dumps(rows[:3], ensure_ascii=False)


def tool_time() -> str:
    curr_dt = datetime.datetime.now()
    cur_d, cur_t = str(curr_dt).split()
    return f"Дата: {cur_d}; время: {cur_t}"


# ---agent loop---


def run_tool(call: dict[str, Any]) -> str:
    name = call["function"]["name"]
    arguments = call["function"]["arguments"]
    print(f"[sys] model wants to call [{name}] {arguments}")
    if name not in TOOL_NAMES:  # модель не должна вызвать произвольную функцию модуля
        return f"Неизвестный инструмент: {name}"
    try:
        # globals() — словарь "имя -> объект" всех имён этого файла, Python ведёт его сам
        return globals()[name](**arguments)
    except Exception as e:  # ошибку отдаём модели строкой, а не роняем цикл
        handle_exception(e, "requests")
        return f"Ошибка инструмента {name}: {type(e).__name__}"


def answer_with_tools() -> str:
    for _ in range(MAX_STEPS):
        message = get_response(cut_history(history))["message"]
        history.append(message)
        calls = message.get("tool_calls")
        if not calls:  # инструменты больше не нужны — это финальный ответ
            return message["content"]
        for call in calls:  # все вызовы из сообщения, не только первый
            history.append(
                {
                    "role": "tool",
                    "tool_name": call["function"]["name"],
                    "content": run_tool(call),
                }
            )
    stop = "Слишком много вызовов инструментов подряд, остановился."
    history.append({"role": "assistant", "content": stop})
    return stop


def agent_loop() -> None:
    while True:
        prompt = input("Enter you message for model:\n")
        if not prompt.strip():
            continue
        if prompt.lower() in ("exit", "выход"):
            break
        turn_start = len(history)
        try:
            history.append({"role": "user", "content": prompt})
            print(f"[LLM]: {answer_with_tools()}")
        except Exception as e:
            del history[turn_start:]  # откат: не оставляем в истории оборванный вызов
            handle_exception(e, "requests")


if __name__ == "__main__":
    agent_loop()
