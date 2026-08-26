import requests

from config import URL, TIMEOUT
from tools_registry import tools

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


def send_request(messages, use_tools=True):
    payload = {
        "model": "qwen3.5:9b",
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
