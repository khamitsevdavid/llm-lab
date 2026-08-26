# Chat Bot с Tool Calling

Чат-бот с поддержкой tool calling: сам решает, когда вызвать функцию (узнать время, получить новости), а когда просто ответить текстом.

## Что умеет

- Вызывает `get_current_datetime` для текущей даты/времени/дня недели
- Вызывает `get_news(topic, limit)` для свежих новостей из RSS (Хабр, Lenta)
- Блокирует китайский язык в ответах и переформулирует на русский
- Хранит историю диалога (последние 5 ходов)

## Архитектура

```
Пользователь
    ↓
main.py (цикл диалога)
    ↓
llm_client.py (send_request) ──→ Ollama API (localhost:11434) ──→ Qwen 3.5 9b
    ↓
tools_registry.py (execute_tool)
    ↓
tools_news.py / tools_time.py (реальное выполнение)
```

Проект разбит на модули с чёткой ответственностью:

| Файл | Что делает |
|---|---|
| `config.py` | Все константы (URL, таймауты, лимиты) |
| `tools_news.py` | Получение новостей из RSS |
| `tools_time.py` | Получение текущей даты/времени |
| `tools_registry.py` | Список доступных инструментов + диспетчер вызовов |
| `llm_client.py` | Отправка запросов к модели |
| `history.py` | Хранение и подготовка истории диалога |
| `validators.py` | Проверка и постобработка ответа модели |
| `main.py` | Точка входа — цикл диалога с пользователем |

## Требования

- Python 3.12+
- Ollama (для локальной модели) **или** API-ключ облачного провайдера (см. ниже)
- 8GB RAM минимум для Qwen 3.5 9b (не нужно, если используете облачный API)
- Доступ в интернет для RSS и/или облачного API

## Установка и запуск (с Ollama, по умолчанию)

```bash
pip install requests feedparser
ollama pull qwen3.5:9b
ollama serve
python3 main.py
```

## Подключение своего провайдера LLM (например, OpenAI)

Сейчас `llm_client.py` жёстко обращается к Ollama по адресу `localhost:11434`. Чтобы подключить другого провайдера, нужно заменить только один файл — остальной код (`main.py`, `history.py`, `tools_registry.py`) трогать не придётся.

### Шаг 1. Установите библиотеку провайдера

```bash
pip install openai
```

### Шаг 2. Задайте API-ключ

```bash
export OPENAI_API_KEY="ваш-ключ"
```

### Шаг 3. Замените функцию `send_request` в `llm_client.py`

Текущая версия отправляет запрос в формате Ollama. Вот пример эквивалента для OpenAI — сигнатура функции (имя, аргументы, что возвращает) остаётся такой же, поэтому весь остальной код продолжит работать без изменений:

```python
import openai

client = openai.OpenAI()  # ключ берётся из переменной окружения OPENAI_API_KEY


def send_request(messages, use_tools=True):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools if use_tools else None,
        )
    except Exception as error:
        print(f"❌ Ошибка соединения: {error}")
        return None

    choice = response.choices[0].message

    # приводим ответ к тому же виду, что ожидает остальной код
    return {
        "message": {
            "role": "assistant",
            "content": choice.content or "",
            "tool_calls": [
                {
                    "id": call.id,
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
                for call in (choice.tool_calls or [])
            ],
        }
    }
```

Важная деталь: `tool_calls[].function.arguments` у OpenAI приходит **строкой** (JSON), а не готовым словарём — но в `tools_registry.py` это уже обрабатывается (`execute_tool` делает `json.loads`, если аргументы пришли строкой), так что дополнительно ничего чинить не нужно.

### Другие провайдеры

Тот же принцип подойдёт для Anthropic (Claude), Google (Gemini) или любого другого API с поддержкой tool calling — меняется только тело `send_request` и формат приведения ответа к общему виду `{"message": {...}}`.

## Доступные инструменты

**`get_current_datetime()`** — возвращает текущую дату, время и день недели.

**`get_news(topic, limit)`** — получает новости из RSS-ленты.

Поддерживаемые темы:

| Тема | Источник |
|---|---|
| `python` | Хабр / Python |
| `llm`, `ai`, `ml` | Хабр / Machine Learning |
| `news` | Lenta.ru |
| `tech` | Хабр / IT Infrastructure |
| `all` | Хабр / все статьи |

## Известные ограничения

- Qwen 3.5 9b (reasoning) на данный момент имеет известный баг совместимости с Ollama при tool calling — иногда не выполняет вызов вообще
- RSS возвращает только последние N статей ленты целиком, не умеет искать по конкретной теме внутри ленты
- Тема `tech` (`feeds['tech']`) сейчас ведёт на несуществующую ссылку Хабра — известная проблема, требует замены URL