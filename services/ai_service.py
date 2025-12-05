import json
import google.generativeai as genai
from app.config import settings

genai.configure(api_key=settings.gemini_api_key)
model = genai.GenerativeModel("gemini-1.5-flash")


def parse_student_request(user_query):
    prompt = f"""Ты ассистент для абитуриентов Казахстана.
Распарси запрос студента и верни ТОЛЬКО валидный JSON.

Запрос: {user_query}

JSON:"""

    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()

        # Убираем markdown блоки
        if "json" in response_text and "```" in response_text:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            response_text = response_text[start:end]

        parsed = json.loads(response_text)

        return {
            "ent_score": parsed.get("ent_score"),
            "preferred_city": parsed.get("preferred_city"),
            "preferred_specialties": parsed.get("preferred_specialties", []),
            "budget": parsed.get("budget", "any")
        }

    except Exception as e:
        print(f"Error: {e}")
        return {
            "ent_score": None,
            "preferred_city": None,
            "preferred_specialties": [],
            "budget": "any"
        }


def generate_ai_explanation(university_name, student_ent, uni_min_ent, specialties_match, grant_chance):
    if specialties_match:
        specs = ", ".join(specialties_match)
    else:
        specs = "нет данных"

    prompt = f"""Вуз: {university_name}
ЕНТ студента: {student_ent}
Минимальный ЕНТ: {uni_min_ent}
Специальности: {specs}
Шансы на грант: {grant_chance}

Напиши короткое объяснение на русском."""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()

    except Exception as e:
        print(f"Error: {e}")
        return f"Вуз {university_name} хороший выбор!"
