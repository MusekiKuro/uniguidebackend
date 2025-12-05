import json
from pathlib import Path
from typing import List, Tuple
from models.university import StudentRequest


def load_universities():
    """Загружает данные вузов из JSON-файла."""
    data_path = Path(__file__).parent.parent / "data" / "universities.json"
    # Убедитесь, что ваш JSON-файл существует и путь корректен
    if not data_path.exists():
        # Если файл не найден, возвращаем пустой список, чтобы избежать ошибки
        print("Warning: universities.json not found!")
        return []

    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def filter_universities(ent_score, preferred_city=None, preferred_specialties=None, budget="any"):
    """
    Фильтрует вузы по базовым критериям (ЕНТ, город, специальность, грант).
    Возвращает неотсортированный список всех подходящих вузов.
    """
    universities = load_universities()
    filtered = []

    for uni in universities:
        # Фильтр по ЕНТ: допуск даже при небольшом недоборе (-5 баллов)
        if ent_score is not None and ent_score < uni["min_ent_score"] - 5:
            continue

        # Фильтр по городу
        if preferred_city and uni["city"].lower() != preferred_city.lower():
            continue

        # Фильтр по специальностям (проверяем программы)
        if preferred_specialties:
            programs = uni.get("programs", [])
            # Проверяем совпадение по названию, коду или группе
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

        # Фильтр по гранту
        if budget == "grant":
            programs_with_grant = [p for p in uni.get("programs", []) if p.get("grant_available")]
            if not programs_with_grant:
                continue

        filtered.append(uni)

    # Возвращаем список без сортировки, так как сортировка будет в главной функции
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
    if score_diff >= 10:
        base_chance = 90.0
    elif score_diff >= 5:
        base_chance = 70.0
    elif score_diff >= 0:
        base_chance = 40.0
    elif score_diff >= -5:
        base_chance = 20.0
    else:
        base_chance = 5.0

        # Корректировка по проценту грантов на программе (квота)
    if program_grant_percent < 30:
        base_chance *= 0.8
    elif program_grant_percent > 50:
        base_chance *= 1.1

    final_chance = min(100.0, max(0.0, base_chance))

    if final_chance >= 70:
        return ("Высокие", final_chance)
    elif final_chance >= 30:
        return ("Средние", final_chance)
    else:
        return ("Низкие", final_chance)


def calculate_match_score(ent_score, uni_min_score, uni_rating, matching_count):
    """
    Расчет Match Score (0-100) на основе баллов, совпадения специальностей и рейтинга.
    """
    score = 0.0

    # 1. Вес за балл ЕНТ (40%)
    if ent_score:
        ent_diff = ent_score - uni_min_score
        if ent_diff >= 10:
            score += 40
        elif ent_diff >= 0:
            score += 30
        elif ent_diff >= -5:
            score += 15
        else:
            score += 5
    else:
        score += 20

        # 2. Вес за совпадение специальностей (30%)
    score += min(30, matching_count * 10)

    # 3. Вес за рейтинг вуза (30%)
    # Нормализация: 5.0 -> 30 баллов, 3.0 -> 0 баллов
    normalized_rating = (uni_rating - 3.0) / 2.0 if uni_rating and uni_rating >= 3.0 else 0
    score += normalized_rating * 30

    return round(score, 1)


def recommend_by_structured_data(request: StudentRequest):
    """
    Главная функция для получения рекомендаций по структурированному запросу.
    """
    ent_score = request.ent_score
    preferred_city = request.preferred_city
    preferred_specialties = request.preferred_specialties
    budget = request.budget

    # 1. Фильтрация
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

            # Проверка совпадения специальностей
            for spec in preferred_specialties:
                spec_lower = spec.lower()

                # Приоритет совпадениям по кодам
                if (prog.get("group_code") and spec_lower == prog["group_code"].lower()) or \
                        (prog.get("code") and spec_lower == prog["code"].lower()) or \
                        (spec_lower in prog["name"].lower()):
                    is_match = True
                    break

            if is_match:
                matching_count += 1
                matching_specs.append(prog["name"])

                # Выбираем программу с самым высоким проходным баллом для расчета шансов
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
            # Фоллбэк: используем общий мин. балл вуза, если программа не найдена
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

    # 2. Сортировка по Match Score и ограничение топ-5
    recommendations.sort(key=lambda x: x["match_score"], reverse=True)

    return recommendations[:5]  # Возвращаем топ-5 рекомендаций