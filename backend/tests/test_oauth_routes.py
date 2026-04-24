import os

from fastapi.testclient import TestClient

os.environ["APP_ENV"] = "testing"
os.environ["DEBUG"] = "true"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/agentic_bay_test"
os.environ["DATABASE_URL_SYNC"] = (
    "postgresql+psycopg2://postgres:postgres@localhost:5432/agentic_bay_test"
)
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

from app.core.config import settings
from app.main import app


def test_google_auth_route_returns_configured_auth_url() -> None:
    original_value = settings.GOOGLE_AUTH_URL
    settings.GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth?client_id=test"
    client = TestClient(app)

    try:
        response = client.get("/api/auth/google")
    finally:
        settings.GOOGLE_AUTH_URL = original_value

    assert response.status_code == 200
    assert response.json() == {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=test"
    }


def test_facebook_auth_route_returns_service_unavailable_when_unconfigured() -> None:
    original_value = settings.FACEBOOK_AUTH_URL
    settings.FACEBOOK_AUTH_URL = None
    client = TestClient(app)

    try:
        response = client.get("/api/auth/facebook")
    finally:
        settings.FACEBOOK_AUTH_URL = original_value

    assert response.status_code == 503
    assert response.json()["detail"] == "Facebook sign-in is not configured."
