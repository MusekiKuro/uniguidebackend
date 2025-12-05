# models/university.py
from pydantic import BaseModel, Field
from typing import List, Optional

class StudentRequest(BaseModel):
    ent_score: Optional[int] = Field(None, ge=0, le=140)
    preferred_city: Optional[str] = None
    preferred_specialties: Optional[List[str]] = Field(default_factory=list)
    budget: Optional[str] = "any"

class Program(BaseModel):
    """Программа обучения"""
    name: str
    code: Optional[str] = None        # Например: "6B06101" (код самой программы)
    group_code: Optional[str] = None  # Например: "B057" (Группа образовательных программ - важно для гранта!)
    careers: List[str] = Field(default_factory=list) # Кем можно работать: ["Backend Dev", "System Architect"]
    duration: str
    cost_per_year: Optional[int] = None
    grant_available: bool = False
    grant_percent: int = 0
    min_ent_score: int

class Dormitory(BaseModel):
    available: bool
    cost_per_month: Optional[int] = None

class University(BaseModel):
    id: int
    name: str
    city: str
    type: str
    description: str
    min_ent_score: int
    programs: List[Program]
    dormitory: Dormitory
    website: Optional[str] = None
    tour_images: List[str] = Field(default_factory=list)
    partnerships: List[str] = Field(default_factory=list)
    rating: Optional[float] = None

class RecommendationResponse(BaseModel):
    university: dict
    match_score: float
    grant_chance: str
    grant_percentage: float
    matching_specialties: List[str]