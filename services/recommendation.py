import json
from pathlib import Path
from typing import List, Tuple
from models.university import StudentRequest


def load_universities():
    """Загружает данные вузов из JSON-файла."""
    data_path = Path(__file__).parent.parent / "data" / "universities.json"
    if not data_path.exists():
        print("Warning: universities.json not found!")
        return []

    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def filter_universities(ent_score, preferred_city=None, preferred_specialties=None, budget="any"):
    """
    Фильтрует вузы по базовым критериям (ЕНТ, город, специальность, грант).
    """
    universities = load_universities()
    filtered = []

    for uni in universities:
        # Фильтр по ЕНТ: допуск даже при небольшом недоборе (-5 баллов)
        if ent_score is not None and ent_score < uni["min_ent_score"] - 5:
            continue

        if preferred_city and uni["city"].lower() != preferred_city.lower():
            continue

        if preferred_specialties:
            programs = uni.get("programs", [])
            has_specialty = any(
                any(
                    spec.lower() in prog["name"].lower() or
                    (prog.get("group_code") and spec.upper() == prog["group_code"].upper()) or
                    (prog.get("code") and spec.upper() == prog["code"].upper())
                    for spec in preferred_specialties
                )
                for prog in programs
            )
            if not has_specialty:
                continue

        if budget == "grant":
            programs_with_grant = [p for p in uni.get("programs", []) if p.get("grant_available")]
            if not programs_with_grant:
                continue

        filtered.append(uni)

    return filtered


def calculate_grant_chance(ent_score: int, program_min_score: int, program_grant_percent: int) -> Tuple[str, float]:
    """
    Рассчитывает шансы на грант с учетом проходного балла и квоты программы.
    """
    if ent_score is None:
        return ("Неизвестно", 0)

    score_diff = ent_score - program_min_score
    base_chance = 0.0

    # Оценка шанса на основе разницы ЕНТ
    if score_diff >= 20:
        base_chance = 95.0
    elif score_diff >= 10:
        base_chance = 85.0
    elif score_diff >= 5:
        base_chance = 70.0
    elif score_diff >= 0:
        base_chance = 50.0
    elif score_diff >= -5:
        base_chance = 25.0
    else:
        base_chance = 10.0

    # Корректировка по проценту грантов на программе (квота)
    if program_grant_percent < 30:
        base_chance *= 0.85
    elif program_grant_percent > 50:
        base_chance *= 1.1

    final_chance = min(100.0, max(0.0, base_chance))

    if final_chance >= 70:
        return ("Высокие", final_chance)
    elif final_chance >= 40:
        return ("Средние", final_chance)
    else:
        return ("Низкие", final_chance)


def calculate_match_score(ent_score, uni_min_score, uni_rating, matching_count):
    """
    Расчет Match Score (0-100) на основе баллов, совпадения специальностей и рейтинга.
    Улучшенная логика для высоких баллов ЕНТ.
    """
    score = 0.0

    # 1. Вес за балл ЕНТ (50%) - Увеличено значение
    if ent_score:
        ent_diff = ent_score - uni_min_score
        
        # Улучшенная логика: чем выше балл, тем лучше совпадение
        if ent_diff >= 20:
            score += 50  # Отлично
        elif ent_diff >= 10:
            score += 45  # Очень хорошо
        elif ent_diff >= 5:
            score += 40  # Хорошо
        elif ent_diff >= 0:
            score += 30  # Достаточно
        elif ent_diff >= -5:
            score += 15  # На грани
        else:
            score += 5   # Низкий
    else:
        score += 20

    # 2. Вес за совпадение специальностей (30%)
    # Каждое совпадение +15 баллов, максимум 30
    score += min(30, matching_count * 15)

    # 3. Вес за рейтинг вуза (20%)
    if uni_rating and uni_rating >= 3.0:
        normalized_rating = (uni_rating - 3.0) / 2.0
        score += normalized_rating * 20
    else:
        score += 5  # Минимальный бонус для низкого рейтинга

    return round(min(100, score), 1)


def recommend_by_structured_data(request: StudentRequest):
    """
    Главная функция для получения рекомендаций по структурированному запросу.
    """
    ent_score = request.ent_score
    preferred_city = request.preferred_city
    preferred_specialties = request.preferred_specialties
    budget = request.budget

    filtered_unis = filter_universities(ent_score, preferred_city, preferred_specialties, budget)
    recommendations = []

    for uni in filtered_unis:
        uni_rating = uni.get("rating", 3.0)
        matching_specs = []
        matching_count = 0

        best_program = None
        best_min_ent_score = -1

        for prog in uni.get("programs", []):
            is_match = False

            for spec in preferred_specialties:
                spec_lower = spec.lower()

                if (prog.get("group_code") and spec_lower == prog["group_code"].lower()) or \
                        (prog.get("code") and spec_lower == prog["code"].lower()) or \
                        (spec_lower in prog["name"].lower()):
                    is_match = True
                    break

            if is_match:
                matching_count += 1
                matching_specs.append(prog["name"])

                if prog["min_ent_score"] > best_min_ent_score:
                    best_min_ent_score = prog["min_ent_score"]
                    best_program = prog

        # Расчет шансов на грант
        if best_program and ent_score:
            grant_chance, grant_percentage = calculate_grant_chance(
                ent_score,
                best_program["min_ent_score"],
                best_program.get("grant_percent", 50)
            )
        else:
            grant_chance, grant_percentage = calculate_grant_chance(
                ent_score,
                uni["min_ent_score"],
                50
            )

        # Расчет итогового Match Score
        match_score = calculate_match_score(
            ent_score,
            uni["min_ent_score"],
            uni_rating,
            matching_count
        )

        recommendations.append({
            "university": uni,
            "match_score": match_score,
            "grant_chance": grant_chance,
            "grant_percentage": grant_percentage,
            "matching_specialties": list(set(matching_specs))
        })

    # Сортировка по Match Score
    recommendations.sort(key=lambda x: x["match_score"], reverse=True)

    return recommendations[:5]