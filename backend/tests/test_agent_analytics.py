import os
from datetime import UTC, datetime

from fastapi.testclient import TestClient

os.environ["APP_ENV"] = "testing"
os.environ["DEBUG"] = "true"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://postgres:postgres@localhost:5432/agentic_bay_test"
)
os.environ["DATABASE_URL_SYNC"] = (
    "postgresql+psycopg2://postgres:postgres@localhost:5432/agentic_bay_test"
)
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

from app.main import app
from app.services.agent_analytics import AgentAnalyticsService


def test_agent_analytics_service_calculates_consistent_sections_for_selected_range() -> None:
    service = AgentAnalyticsService(now=datetime(2026, 4, 23, 12, 0, tzinfo=UTC))

    result = service.get_agent_analytics("northstar-research", "30d")

    assert result.agent_id == "northstar-research"
    assert result.range == "30d"
    assert result.summary.total_jobs > 0
    assert len(result.revenue_series) == 6
    assert round(sum(item.percentage for item in result.action_breakdown), 1) == 100.0
    assert (
        sum(item.count for item in result.response_time_distribution) == result.summary.total_jobs
    )
    assert len(result.reviews) == 5
    assert result.reviews == sorted(
        result.reviews, key=lambda review: review.created_at, reverse=True
    )


def test_agent_analytics_service_returns_recent_reviews_for_short_ranges() -> None:
    service = AgentAnalyticsService(now=datetime(2026, 4, 23, 12, 0, tzinfo=UTC))

    result = service.get_agent_analytics("northstar-research", "7d")

    assert len(result.reviews) == 5
    assert all(
        review.created_at >= datetime(2026, 4, 16, 12, 0, tzinfo=UTC) for review in result.reviews
    )


def test_agent_analytics_endpoint_returns_not_found_for_unknown_agent() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/agents/unknown-agent/analytics?range=30d")

    assert response.status_code == 404
    assert response.json()["detail"] == "Agent 'unknown-agent' could not be found."


def test_agent_analytics_endpoint_returns_expected_shape() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/agents/northstar-research/analytics?range=90d")

    assert response.status_code == 200
    body = response.json()
    assert body["agentId"] == "northstar-research"
    assert body["range"] == "90d"
    assert len(body["revenueSeries"]) == 6
    assert len(body["reviews"]) == 5
    assert len(body["responseTimeDistribution"]) == 5
