# app/services/ai_service.py
import json
from anthropic import Anthropic
from app.config import settings

client = Anthropic()

def parse_student_request(user_query: str) -> dict:
    """
    Парсит запрос абитуриента через Claude API.

    Входные данные: "Я набрал 90 баллов на ЕНТ, хочу IT в Алматы с грантом"
    Выход: {
        "ent_score": 90,
        "preferred_city": "Алматы",
        "preferred_specialties": ["IT"],
        "budget": "grant"
    }
    """

    system_prompt = """Ты — ассистент для абитуриентов Казахстана. 
    Твоя задача — распарсить запрос студента и вернуть JSON с ключами:
    - ent_score (int, 0-150): баллы ЕНТ (если не указаны, верни null)
    - preferred_city (str): город (Астана, Алматы, Тараз и т.д.). Если не указан, верни null
    - preferred_specialties (list): направления (IT, Инженерия, Педагогика и т.д.). Если не указаны, верни []
    - budget (str): "grant" если ищет грант, "paid" если платное, "any" если всё равно

    Вернись ТОЛЬКО валидным JSON, без лишнего текста."""

    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=200,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_query}
            ]
        )

        response_text = message.content[0].text.strip()

        # Парсим JSON
        parsed = json.loads(response_text)

        # Валидация
        result = {
            "ent_score": parsed.get("ent_score"),
            "preferred_city": parsed.get("preferred_city"),
            "preferred_specialties": parsed.get("preferred_specialties", []),
            "budget": parsed.get("budget", "any")
        }

        return result

    except json.JSONDecodeError:
        # Если Claude вернул невалидный JSON, возвращаем пустой результат
        return {
            "ent_score": None,
            "preferred_city": None,
            "preferred_specialties": [],
            "budget": "any"
        }
    except Exception as e:
        print(f"Ошибка при парсинге запроса: {e}")
        return {
            "ent_score": None,
            "preferred_city": None,
            "preferred_specialties": [],
            "budget": "any"
        }

def generate_ai_explanation(university_name: str, student_ent: int, uni_min_ent: int,
                            specialties_match: list, grant_chance: str) -> str:
    """
    Генерирует объяснение через Claude, почему этот вуз подходит.

    Пример: "КБТУ подходит тебе, потому что твой ЕНТ (92) выше минимума (80),
    есть IT-программа, и твои шансы на грант — средние."
    """

    system_prompt = """Ты — ассистент для абитуриентов. 
    Напиши короткое, понятное объяснение (1-2 предложения), почему этот вуз подходит студенту.
    Используй РУССКИЙ язык. Будь позитивен и мотивирующий."""

    user_prompt = f"""
    Вуз: {university_name}
    ЕНТ студента: {student_ent}
    Минимальный ЕНТ в вузе: {uni_min_ent}
    Совпадающие специальности: {', '.join(specialties_match)}
    Шансы на грант: {grant_chance}

    Напиши объяснение, почему этот вуз подходит.
    """

    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=150,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )

        return message.content[0].text.strip()

    except Exception as e:
        print(f"Ошибка при генерации объяснения: {e}")
        return f"Вуз {university_name} — хороший выбор для твоего профиля."
