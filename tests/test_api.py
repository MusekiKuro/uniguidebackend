# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """Тест health endpoint"""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_get_universities():
    """Тест получения всех вузов"""
    response = client.get("/api/universities")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert len(data["universities"]) > 0


def test_recommend_endpoint():
    """Тест рекомендаций"""
    payload = {
        "ent_score": 90,
        "preferred_city": "Алматы",
        "preferred_specialties": ["IT"],
        "budget": "grant"
    }
    response = client.post("/api/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert "recommendations" in data
