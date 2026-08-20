# Chat Bot с Tool Calling

Чат-бот на базе локальной LLM Qwen 2.5 7b через Ollama.

# Что умеет

- Вызывает `get_current_datetime` для текущей даты/времени
- Вызывает `get_news` для свежих новостей из RSS (Хабр, Lenta)
- Блокирует китайский язык в ответах и переформулирует на русский
- Хранит историю диалога (последние 5 ходов)

# Архитектура

Пользователь
    ↓
chat_bot.py
    ↓
Ollama API (localhost:11434)
    ↓
Qwen 2.5 7b

# Зависимости

requests feedparser

# Ограничения

- Qwen 2.5 7b нестабильно работает с tool calling (иногда выдумывает даты)
- RSS возвращает только последние N статей, не умеет искать по теме

## Подключение к LLM OpenAI API(в теории)

=== <python>

import openai
client = openai.OpenAI(api_key="your-api-key")
response = client.chat.completions.create(
    model="gpt-3.5-turbo", messages=[{"role": "user", "content": question}]
)
answer = response.choices[0].message.content

=== <python>


# Доступные инструменты

get_current_datetime - Возвращает текущую дату/время/день недели/все вместе.
get_news(topic, limit) - Получает новости из RSS-лент.

# Поддерживаемые темы:

`python` | Хабр Python
`llm`, `ai`, `ml` | Хабр Machine Learning 
`news` | Lenta.ru 
`tech` | Хабр IT Infrastructure 
`all` | Хабр все статьи 

## Требования

- Python 3.12+
- Ollama (для локальной модели)
- 8GB RAM минимум для Qwen 2.5 7b
- Доступ в интернет для RSS