import requests
import json

# Адрес локальной Ollama
URL = "http://localhost:11434/api/generate"

# Тело запроса (payload)
payload = {
    "model": "qwen2.5:7b",
    "prompt": "Привет! Объясни простыми словами, что такое нейросеть. Максимум 3 предложения.",
    "stream": False,  # False = получить весь ответ сразу, а не по кусочкам
}

print("🤖 Отправляю запрос к локальной модели...")
print(f"📝 Промпт: {payload['prompt']}\n")

# Отправляем POST-запрос
response = requests.post(URL, json=payload)

# Проверяем, что всё хорошо
if response.status_code == 200:
    # Парсим JSON-ответ
    data = response.json()

    # Достаём текст ответа
    answer = data["response"]

    print("✅ Ответ от LLM:")
    print("=" * 50)
    print(answer)
    print("=" * 50)
else:
    print(f"❌ Ошибка: {response.status_code}")
    print(response.text)
