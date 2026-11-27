from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_generation_is_not_claimed_as_available() -> None:
    response = client.get("/api/v1/capabilities")
    assert response.status_code == 200
    assert response.json()["speech_generation"] is False
