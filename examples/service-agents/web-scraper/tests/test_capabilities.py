import pytest
from fastapi.testclient import TestClient

from src.main import app

VALID_KEY = "test-orchestrator-key"


@pytest.fixture()
def client():
    return TestClient(app)


def test_capabilities_returns_capability_document(client):
    response = client.get("/capabilities", headers={"x-orchestrator-key": VALID_KEY})

    assert response.status_code == 200
    body = response.json()
    assert "message" in body
    assert "scrape_url" in body["message"].lower()
    assert "PAYMENT" in body["message"]


def test_capabilities_returns_401_without_key(client):
    response = client.get("/capabilities")

    assert response.status_code == 422


def test_capabilities_returns_401_with_wrong_key(client):
    response = client.get("/capabilities", headers={"x-orchestrator-key": "wrong-key"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid orchestrator key"


def test_health_endpoint_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["agent"] == "web-scraper"
    assert "active_sessions" in body
