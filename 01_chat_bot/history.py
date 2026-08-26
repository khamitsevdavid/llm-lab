from config import MAX_TURNS
from llm_client import system_message


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
