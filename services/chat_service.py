import json
import google.generativeai as genai
from app.config import settings
from typing import Dict, Any

# Настраиваем API (ключ берется из app/config.py)
genai.configure(api_key=settings.gemini_api_key)
model = genai.GenerativeModel("gemini-pro")

SYSTEM_PROMPT = """Ты - интерактивный AI-помощник для абитуриентов Казахстана, помогающий выбрать университет.
Твоя цель - собрать ВСЕ недостающие данные для финального подбора вузов:
1. ent_score (баллы ЕНТ, тип: int, max 140)
2. preferred_city (Город, тип: str)
3. preferred_specialties (Специальность/группа ГОП, тип: List[str])
4. budget (Бюджет: "grant", "paid" или "any")

Твой ответ должен быть ВСЕГДА ТОЛЬКО валидным JSON.
JSON должен содержать два ключа:
1. "state": Обновленный объект StudentRequest (обновляй только заполненные пользователем поля, остальные оставляй как есть).
2. "response": Твой ответ пользователю (string).

Если все поля (ent_score, preferred_city, preferred_specialties) заполнены, то в поле "response" скажи, что данные готовы, и можно приступать к поиску.
Будь краток и вежлив. Задавай только один вопрос за раз, чтобы продвинуть беседу.
"""


def chat_step(user_message: str, current_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Обрабатывает один шаг чата, обновляет состояние и генерирует ответ AI.
    """

    # Защита от отсутствия ключей в state
    safe_state = {
        "ent_score": current_state.get("ent_score"),
        "preferred_city": current_state.get("preferred_city"),
        "preferred_specialties": current_state.get("preferred_specialties", []),
        "budget": current_state.get("budget", "any")
    }

    state_str = json.dumps(safe_state)

    prompt = f"""{SYSTEM_PROMPT}

ТЕКУЩЕЕ СОСТОЯНИЕ (НЕ МЕНЯЙТЕ КЛЮЧИ, ИЗМЕНЯЙТЕ ТОЛЬКО ЗНАЧЕНИЯ):
{state_str}

СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ (проанализируй и обнови state):
{user_message}

ОТВЕТ В ФОРМАТЕ JSON:
"""

    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()

        # Убираем markdown блоки, если они есть
        if "json" in response_text and "```" in response_text:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            response_text = response_text[start:end]

        parsed = json.loads(response_text)

        # Проверка структуры ответа
        if "state" not in parsed or "response" not in parsed:
            return {
                "state": safe_state,
                "response": "Извините, произошла внутренняя ошибка обработки AI. Пожалуйста, повторите запрос."
            }

        # Возвращаем обновленный state и ответ AI
        return parsed

    except Exception as e:
        print(f"Chat Service Error: {e}")
        # Возвращаем безопасный fallback
        return {
            "state": safe_state,
            "response": "Извините, не удалось связаться с AI-помощником. Попробуйте еще раз."
        }