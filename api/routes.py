# app/api/routes.py
from fastapi import APIRouter, HTTPException
from typing import List
import json
from pathlib import Path

from models.university import StudentRequest, University
from services.ai_service import parse_student_request, generate_ai_explanation
from services.recommendation import get_recommendations, load_universities


router = APIRouter(prefix="/api", tags=["api"])


@router.post("/recommend")
async def recommend_universities(request: StudentRequest):
    """
    Главный эндпоинт: ИИ-помощник + рекомендации.

    Принимает:
    {
        "ent_score": 90,
        "preferred_city": "Алматы",
        "preferred_specialties": ["IT"],
        "budget": "grant"
    }

    Возвращает:
    {
        "recommendations": [
            {
                "university": {...},
                "match_score": 85.0,
                "grant_chance": "Средние",
                "ai_explanation": "..."
            }
        ]
    }
    """

    # Получаем рекомендации
    recommendations = get_recommendations(
        ent_score=request.ent_score,
        preferred_city=request.preferred_city,
        preferred_specialties=request.preferred_specialties,
        budget=request.budget
    )

    # Для каждой рекомендации генерируем объяснение от ИИ
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


@router.post("/recommend-by-text")
async def recommend_by_text(user_query: dict):
    """
    Альтернативный эндпоинт: парсим текстовый запрос через ИИ.

    Принимает:
    {
        "query": "Я набрал 90 баллов, хочу IT в Алматы с грантом"
    }

    Возвращает то же, что /recommend
    """

    query = user_query.get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="Query не может быть пустым")

    # Парсим запрос через ИИ
    parsed = parse_student_request(query)

    # Создаём StudentRequest из распарсенного запроса
    request = StudentRequest(
        ent_score=parsed["ent_score"],
        preferred_city=parsed["preferred_city"],
        preferred_specialties=parsed["preferred_specialties"],
        budget=parsed["budget"]
    )

    # Вызываем основную логику
    return await recommend_universities(request)


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
    Сравнить 2-3 вуза.

    Принимает:
    {
        "university_ids": [1, 2, 3]
    }

    Возвращает таблицу с параметрами.
    """

    university_ids = request.get("university_ids", [])
    if not university_ids or len(university_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="Нужно выбрать минимум 2 вуза"
        )

    universities = load_universities()
    selected = []

    for uni_id in university_ids:
        for uni in universities:
            if uni["id"] == uni_id:
                selected.append(uni)
                break

    if not selected:
        raise HTTPException(status_code=404, detail="Вузы не найдены")

    return {
        "success": True,
        "comparison": selected
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
