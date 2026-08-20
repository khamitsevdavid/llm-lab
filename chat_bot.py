import json
import re
from datetime import datetime

import feedparser
import requests


URL = "http://localhost:11434/api/chat"

MAX_TURNS = 5
MAX_TOOL_CALLS = 3
TIMEOUT = 60
MAX_NEWS = 10


def has_chinese(text):
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def get_current_datetime():
    now = datetime.now()

    weekdays = [
        "понедельник",
        "вторник",
        "среда",
        "четверг",
        "пятница",
        "суббота",
        "воскресенье",
    ]

    weekday = weekdays[now.weekday()]

    return now.strftime("%Y-%m-%d %H:%M:%S") + f" ({weekday})"


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


system_message = {
    "role": "system",
    "content": (
        "Ты дружелюбный помощник по имени Qwen. "
        "Отвечай ТОЛЬКО на русском языке. "
        "НИКОГДА не выдумывай даты и время — всегда вызывай get_current_datetime. "
        "У тебя есть два инструмента: "
        "get_current_datetime для даты и времени, "
        "get_news для новостей и статей. "
        "ОБЯЗАТЕЛЬНО используй get_current_datetime когда спрашивают про время, дату или день недели. "
        "Используй get_news когда спрашивают про новости. "
        "Для обычных вопросов отвечай напрямую."
    ),
}


tools = [
    {
        "type": "function",
        "function": {
            "name": "get_current_datetime",
            "description": ("Возвращает текущие дату, время и день недели."),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_news",
            "description": ("Получает свежие новости и статьи из RSS."),
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "enum": [
                            "python",
                            "llm",
                            "ai",
                            "ml",
                            "news",
                            "tech",
                            "all",
                        ],
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                    },
                },
                "required": [],
            },
        },
    },
]


history = [system_message]


def build_messages():
    turns = []
    current_turn = []

    for message in history[1:]:
        if message["role"] == "user" and current_turn:
            turns.append(current_turn)
            current_turn = []

        current_turn.append(message)

    if current_turn:
        turns.append(current_turn)

    recent_turns = turns[-MAX_TURNS:]

    messages = [system_message]

    for turn in recent_turns:
        messages.extend(turn)

    return messages


def send_request(messages, use_tools=True):
    payload = {
        "model": "qwen2.5:7b",
        "messages": messages,
        "stream": False,
    }

    if use_tools:
        payload["tools"] = tools

    try:
        response = requests.post(
            URL,
            json=payload,
            timeout=TIMEOUT,
        )

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as error:
        print(f"❌ Ошибка соединения: {error}")
        return None

    except json.JSONDecodeError:
        print("❌ Ollama вернула некорректный JSON.")
        return None


def execute_tool(tool_call):
    function = tool_call["function"]
    name = function["name"]
    arguments = function.get("arguments", {})

    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            return "Ошибка в аргументах инструмента."

    if name == "get_current_datetime":
        return get_current_datetime()

    if name == "get_news":
        topic = arguments.get("topic", "all")
        limit = arguments.get("limit", 5)

        return get_news(
            topic=topic,
            limit=limit,
        )

    return "Неизвестный инструмент."


def check_answer(answer):
    if not has_chinese(answer):
        return answer

    print("⚠️ Обнаружен китайский текст.")

    evaluation_messages = build_messages()

    evaluation_messages.append(
        {
            "role": "assistant",
            "content": answer,
        }
    )

    evaluation_messages.append(
        {
            "role": "user",
            "content": (
                "Переформулируй свой предыдущий ответ ТОЛЬКО на русском языке."
            ),
        }
    )

    data = send_request(
        evaluation_messages,
        use_tools=False,
    )

    if not data:
        return answer

    new_answer = data["message"].get("content", "")

    if has_chinese(new_answer):
        print("⚠️ Повторный ответ тоже содержит китайский текст.")

    return new_answer


while True:
    question = input("Ты: ")

    if question.lower() in ("выход", "exit"):
        print("Qwen: До встречи!")
        break

    if not question.strip():
        continue

    history.append(
        {
            "role": "user",
            "content": question,
        }
    )

    messages = build_messages()

    data = send_request(
        messages,
        use_tools=True,
    )

    if not data:
        continue

    message = data.get("message")

    if not message:
        print("❌ В ответе Ollama нет message.")
        continue

    tool_iterations = 0

    while message.get("tool_calls") and tool_iterations < MAX_TOOL_CALLS:
        tool_iterations += 1

        tool_results = []

        for tool_call in message["tool_calls"]:
            name = tool_call["function"]["name"]

            print(f"🔧 Qwen хочет вызвать: {name}")

            result = execute_tool(tool_call)

            tool_results.append(
                {
                    "role": "tool",
                    "content": result,
                    "tool_call_id": tool_call["id"],
                }
            )

        history.append(message)

        history.extend(tool_results)

        messages = build_messages()

        data = send_request(
            messages,
            use_tools=True,
        )

        if not data:
            break

        message = data.get("message")

        if not message:
            break

    answer = message.get("content", "")

    if not answer.strip() and tool_iterations > 0:
        print("⚠️ Qwen не дал финальный текст. Запрашиваю ответ ещё раз.")

        fallback_messages = build_messages()

        fallback_messages.append(
            {
                "role": "user",
                "content": "Дай финальный ответ пользователю.",
            }
        )

        data = send_request(
            fallback_messages,
            use_tools=False,
        )

        if data:
            answer = data["message"].get("content", "")

    answer = check_answer(answer)

    print(f"Qwen: {answer}")

    history.append(
        {
            "role": "assistant",
            "content": answer,
        }
    )
