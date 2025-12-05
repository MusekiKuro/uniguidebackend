# app/services/recommendation.py
import json
from pathlib import Path
from typing import List, Tuple
from app.models.university import University, RecommendationResponse


def load_universities() -> List[dict]:
    """Загружаем вузы из JSON."""
    data_path = Path(__file__).parent.parent / "data" / "universities.json"
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_grant_chance(ent_score: int, min_ent_score: int) -> Tuple[str, float]:
    """
    Расчёт шансов на грант (Вариант В).

    Логика:
    - Если ent >= min + 10: Высокие (75%)
    - Если ent >= min: Средние (45%)
    - Иначе: Низкие (15%)

    Возвращает: ("Высокие", 75.0)
    """

    if ent_score is None:
        return ("Неизвестно", 0)

    if ent_score >= min_ent_score + 10:
        return ("Высокие", 75.0)
    elif ent_score >= min_ent_score:
        return ("Средние", 45.0)
    else:
        return ("Низкие", 15.0)


def filter_universities(
        ent_score: int,
        preferred_city: str = None,
        preferred_specialties: List[str] = None,
        budget: str = "any"
) -> List[dict]:
    """
    Фильтрует вузы по критериям абитуриента.

    Возвращает отсортированный по релевантности список вузов.
    """

    universities = load_universities()
    filtered = []

    for uni in universities:
        # Фильтр 1: ЕНТ баллы
        # Если ent_score == None, пропускаем этот фильтр
        if ent_score is not None and ent_score < uni["min_ent_score"] - 5:
            continue  # Слишком низко

        # Фильтр 2: Город
        if preferred_city and uni["city"].lower() != preferred_city.lower():
            continue

        # Фильтр 3: Специальности
        if preferred_specialties:
            has_specialty = any(
                spec.lower() in [s.lower() for s in uni["specialties"]]
                for spec in preferred_specialties
            )
            if not has_specialty:
                continue

        # Фильтр 4: Грант
        if budget == "grant" and uni["grant_places"] == 0:
            continue

        filtered.append(uni)

    # Сортируем по релевантности
    def relevance_score(uni):
        score = 0

        # Близость по ЕНТ (чем ближе, тем лучше)
        if ent_score is not None:
            ent_diff = abs(ent_score - uni["min_ent_score"])
            score += (100 - ent_diff)  # Чем ближе, тем выше
        else:
            score += 50

        # Наличие гранта (если ищет грант)
        if budget == "grant" and uni["grant_places"] > 0:
            score += 30

        # Количество специальностей
        score += len(uni["specialties"]) * 5

        return score

    filtered.sort(key=relevance_score, reverse=True)

    return filtered[:5]  # Возвращаем топ-5


def get_recommendations(
        ent_score: int = None,
        preferred_city: str = None,
        preferred_specialties: List[str] = None,
        budget: str = "any"
) -> List[dict]:
    """
    Главная функция рекомендаций.

    Возвращает список вузов с объяснением и шансами на грант.
    """

    # Фильтруем вузы
    filtered_unis = filter_universities(
        ent_score,
        preferred_city,
        preferred_specialties,
        budget
    )

    recommendations = []

    for uni in filtered_unis[:4]:  # Топ-4 вуза
        # Рассчитываем шансы на грант
        grant_chance, grant_percentage = calculate_grant_chance(
            ent_score,
            uni["min_ent_score"]
        )

        # Совпадающие специальности
        matching_specs = []
        if preferred_specialties:
            matching_specs = [
                spec for spec in uni["specialties"]
                if spec.lower() in [s.lower() for s in preferred_specialties]
            ]

        # Релевантность (простой расчёт)
        match_score = 75.0  # По умолчанию
        if ent_score and ent_score >= uni["min_ent_score"]:
            match_score = 85.0
        if ent_score and ent_score >= uni["min_ent_score"] + 10:
            match_score = 95.0

        recommendations.append({
            "university": {
                "id": uni["id"],
                "name": uni["name"],
                "city": uni["city"],
                "min_ent_score": uni["min_ent_score"],
                "grant_places": uni["grant_places"],
                "specialties": uni["specialties"],
                "description": uni["description"],
                "website": uni.get("website")
            },
            "match_score": match_score,
            "grant_chance": grant_chance,
            "grant_percentage": grant_percentage,
            "matching_specialties": matching_specs
        })

    return recommendations
