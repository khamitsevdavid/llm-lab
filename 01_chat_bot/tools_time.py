from datetime import datetime


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
