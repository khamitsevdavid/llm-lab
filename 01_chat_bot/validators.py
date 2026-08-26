import re

from llm_client import send_request
from history import build_messages


def has_chinese(text):
    return bool(re.search(r"[\u4e00-\u9fff]", text))


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
