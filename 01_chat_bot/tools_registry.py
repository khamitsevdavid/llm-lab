import json

from tools_news import get_news
from tools_time import get_current_datetime

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
