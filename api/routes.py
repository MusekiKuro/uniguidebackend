from fastapi import APIRouter, HTTPException
# Импорт новой логики чата
from services.chat_service import chat_step
from typing import List
import json
from pathlib import Path

from models.university import StudentRequest, University
# Импортируем обе функции из ai_service.py и главную функцию рекомендаций
from services.ai_service import parse_student_request, generate_ai_explanation
from services.recommendation import recommend_by_structured_data, load_universities

router = APIRouter(prefix="/api", tags=["api"])


# ----------------------------------------------------------------------
# Вспомогательная синхронная логика для избежания дублирования кода
# ----------------------------------------------------------------------

def get_recommendations_with_ai_explanation(request: StudentRequest):
    """Объединяет логику рекомендаций и генерацию ИИ-объяснений."""

    # 1. Получаем рекомендации
    recommendations = recommend_by_structured_data(request)

    # 2. Для каждой рекомендации генерируем объяснение от ИИ (Синхронный вызов)
    result = []
    for rec in recommendations:
        explanation = generate_ai_explanation(
            university_name=rec["university"]["name"],
            student_ent=request.ent_score or 0,
            uni_min_ent=rec["university"]["min_ent_score"],
            specialties_match=rec["matching_specialties"],
            grant_chance=rec["grant_chance"]
        )

        result.append({
            "university": rec["university"],
            "match_score": rec["match_score"],
            "grant_chance": rec["grant_chance"],
            "grant_percentage": rec["grant_percentage"],
            "ai_explanation": explanation
        })

    return {
        "success": True,
        "recommendations": result,
        "total_found": len(result)
    }


# ----------------------------------------------------------------------
# 1. Endpoints для рекомендаций (FIXED)
# ----------------------------------------------------------------------

@router.post("/recommend")
async def recommend_universities(request: StudentRequest):
    """
    Главный эндпоинт: ИИ-помощник + рекомендации по структуре.
    """
    try:
        # Вызываем синхронную логику
        return get_recommendations_with_ai_explanation(request)
    except Exception as e:
        # Добавляем более информативный вывод ошибки
        raise HTTPException(status_code=500, detail=f"Recommendation error: {str(e)}")


@router.post("/recommend-by-text")
async def recommend_by_text(user_query: dict):
    """
    Альтернативный эндпоинт: парсим текстовый запрос через ИИ.
    """
    query = user_query.get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="Query не может быть пустым")

    try:
        # Парсим запрос через ИИ (Синхронный вызов. БЕЗ 'await')
        parsed = parse_student_request(query)

        # Создаём StudentRequest из распарсенного запроса
        request = StudentRequest(
            ent_score=parsed.get("ent_score"),
            preferred_city=parsed.get("preferred_city"),
            preferred_specialties=parsed.get("preferred_specialties"),
            budget=parsed.get("budget")
        )

        # Вызываем основную логику
        return get_recommendations_with_ai_explanation(request)  # Синхронный вызов

    except Exception as e:
        # Если ошибка связана с парсингом или Gemini, она будет здесь
        raise HTTPException(status_code=500, detail=f"AI/Recommendation error: {str(e)}")


# ----------------------------------------------------------------------
# 2. Endpoints для работы с вузами
# ----------------------------------------------------------------------

@router.get("/universities")
async def get_all_universities():
    """
    Получить все вузы из базы.
    """
    universities = load_universities()
    return {
        "success": True,
        "universities": universities,
        "total": len(universities)
    }


@router.get("/universities/{university_id}")
async def get_university_details(university_id: int):
    """
    Получить карточку одного вуза.
    """
    universities = load_universities()

    for uni in universities:
        if uni["id"] == university_id:
            return {
                "success": True,
                "university": uni
            }

    raise HTTPException(status_code=404, detail="Вуз не найден")


@router.post("/compare")
async def compare_universities(request: dict):
    """
    Сравнить вузы. Возвращает матрицу сравнения, удобную для табличного отображения.
    """
    university_ids = request.get("university_ids", [])
    if not university_ids or len(university_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="Нужно выбрать минимум 2 вуза для сравнения"
        )

    all_universities = load_universities()
    selected = [u for u in all_universities if u["id"] in university_ids or str(u["id"]) in university_ids]

    if len(selected) < 2:
        raise HTTPException(status_code=404, detail="Выбранные вузы не найдены или их недостаточно")

    # Формируем структуру для таблицы сравнения
    comparison_data = {
        "universities": [{"id": u["id"], "name": u["name"], "city": u["city"]} for u in selected],
        "metrics": [
            {
                "key": "type",
                "label": "Тип вуза",
                "values": [u["type"] for u in selected]
            },
            {
                "key": "min_ent_score",
                "label": "Мин. балл ЕНТ (общий)",
                "values": [u["min_ent_score"] for u in selected]
            },
            {
                "key": "rating",
                "label": "Рейтинг",
                "values": [u.get("rating", "-") for u in selected]
            },
            {
                "key": "dormitory",
                "label": "Общежитие",
                "values": [
                    f"{'Есть' if u['dormitory']['available'] else 'Нет'} ({u['dormitory'].get('cost_per_month', 'N/A')} тг/мес)"
                    for u in selected
                ]
            },
            {
                "key": "programs_count",
                "label": "Количество программ",
                "values": [len(u["programs"]) for u in selected]
            },
            {
                "key": "avg_cost",
                "label": "Средняя стоимость (год)",
                "values": [
                    int(sum(p.get("cost_per_year", 0) or 0 for p in u["programs"]) / len(u["programs"]))
                    if u["programs"] else 0
                    for u in selected
                ]
            }
        ]
    }

    return {
        "success": True,
        "comparison": comparison_data
    }


@router.get("/health")
async def health_check():
    """
    Проверка, что сервер живой.
    """
    return {
        "status": "ok",
        "message": "DataHub Backend работает!"
    }
@router.post("/chat")
async def chat_interaction(request: dict):
    """
    Обрабатывает один шаг диалога. Принимает текущий state и сообщение пользователя.

    Принимает:
    {
        "message": "Хочу на IT",
        "current_state": {...} // StudentRequest object as dict
    }

    Возвращает:
    {
        "state": {...}, // Обновленный StudentRequest
        "response": "Какой у вас балл ЕНТ?" // Ответ AI
    }
    """
    message = request.get("message", "")
    current_state = request.get("current_state", {})

    if not message:
        raise HTTPException(status_code=400, detail="Message не может быть пустым")

    # Вызов конверсационного менеджера
    chat_result = chat_step(message, current_state)

    # Проверка, завершен ли сбор данных
    state = chat_result.get("state", {})

    # Если данные собраны, запускаем рекомендацию через /recommend
    if state.get("ent_score") and state.get("preferred_city") and state.get("preferred_specialties"):
        # Создаём Pydantic модель из собранного state
        student_request = StudentRequest(**state)

        # Вызываем основную логику рекомендаций
        recommendation_response = get_recommendations_with_ai_explanation(student_request)

        # Добавляем рекомендации в финальный ответ чата
        chat_result["recommendations"] = recommendation_response["recommendations"]
        chat_result["total_found"] = recommendation_response["total_found"]

    return chat_result