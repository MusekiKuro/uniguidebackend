# services/recommendation.py
import json
from pathlib import Path
from typing import List, Tuple


def load_universities():
    data_path = Path(__file__).parent.parent / "data" / "universities.json"
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_grant_chance(ent_score, min_ent_score):
    if ent_score is None:
        return ("Неизвестно", 0)

    if ent_score >= min_ent_score + 10:
        return ("Высокие", 75.0)
    elif ent_score >= min_ent_score:
        return ("Средние", 45.0)
    else:
        return ("Низкие", 15.0)


def filter_universities(ent_score, preferred_city=None, preferred_specialties=None, budget="any"):
    universities = load_universities()
    filtered = []

    for uni in universities:
        # Фильтр по ЕНТ
        if ent_score is not None and ent_score < uni["min_ent_score"] - 5:
            continue

        # Фильтр по городу
        if preferred_city and uni["city"].lower() != preferred_city.lower():
            continue

        # Фильтр по специальностям (проверяем программы)
        if preferred_specialties:
            programs = uni.get("programs", [])
            has_specialty = any(
                any(spec.lower() in prog["name"].lower() for spec in preferred_specialties)
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

    # Сортировка
    def relevance_score(uni):
        score = 0
        if ent_score is not None:
            ent_diff = abs(ent_score - uni["min_ent_score"])
            score += (100 - ent_diff)
        else:
            score += 50

        score += len(uni.get("programs", [])) * 5
        return score

    filtered.sort(key=relevance_score, reverse=True)
    return filtered[:5]


def get_recommendations(ent_score=None, preferred_city=None, preferred_specialties=None, budget="any"):
    filtered_unis = filter_universities(ent_score, preferred_city, preferred_specialties, budget)

    recommendations = []

    for uni in filtered_unis[:4]:
        grant_chance, grant_percentage = calculate_grant_chance(ent_score, uni["min_ent_score"])

        # Совпадающие специальности
        matching_specs = []
        if preferred_specialties:
            programs = uni.get("programs", [])
            for prog in programs:
                for spec in preferred_specialties:
                    if spec.lower() in prog["name"].lower():
                        matching_specs.append(prog["name"])

        # Match score
        match_score = 75.0
        if ent_score and ent_score >= uni["min_ent_score"]:
            match_score = 85.0
        if ent_score and ent_score >= uni["min_ent_score"] + 10:
            match_score = 95.0

        recommendations.append({
            "university": uni,
            "match_score": match_score,
            "grant_chance": grant_chance,
            "grant_percentage": grant_percentage,
            "matching_specialties": matching_specs
        })

    return recommendations
