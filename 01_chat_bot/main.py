from tools_news import get_news
from config import MAX_TURNS, MAX_TOOL_CALLS, URL, TIMEOUT
from tools_time import get_current_datetime
from tools_registry import tools, execute_tool
from llm_client import send_request, system_message
from history import history, build_messages
from validators import has_chinese, check_answer

if __name__ == "__main__":
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
