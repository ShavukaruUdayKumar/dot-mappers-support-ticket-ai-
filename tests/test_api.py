"""Basic API endpoint tests."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import pandas as pd


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        'ticket_id': ['TKT-001', 'TKT-002', 'TKT-003'],
        'created_at': pd.to_datetime(['2024-01-01', '2024-01-02', '2024-01-03']),
        'category': ['Billing', 'Technical', 'General'],
        'priority': ['Critical', 'High', 'Low'],
        'status': ['Open', 'Resolved', 'Escalated'],
        'response_time_hrs': [1.5, 2.0, 3.0],
        'resolution_time_hrs': [None, 10.0, None],
        'agent_id': ['AGT-01', 'AGT-02', 'AGT-03'],
        'customer_rating': [None, 4, None],
        'issue_summary': ['Billing issue', 'Login failure', 'General query']
    })


@pytest.fixture
def client(sample_df):
    from app.data.loader import data_loader
    data_loader.df = sample_df
    data_loader._loaded = True

    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


def test_ping(client):
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["data_loaded"] is True
    assert data["total_tickets"] == 3


def test_get_stats(client):
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_tickets"] == 3
    assert data["open_tickets"] == 1
    assert data["resolved_tickets"] == 1
    assert data["escalated_tickets"] == 1


def test_get_schema(client):
    response = client.get("/schema")
    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 3
    assert data["total_columns"] == 10
    assert len(data["columns"]) == 10


def test_query_empty_question(client):
    response = client.post("/query", json={"question": ""})
    assert response.status_code == 422  # Pydantic validation error


def test_query_too_short(client):
    response = client.post("/query", json={"question": "Hi"})
    assert response.status_code == 422  # min_length=3 enforced


def test_anomalies_returns_report(client):
    response = client.get("/anomalies")
    assert response.status_code == 200
    data = response.json()
    assert "total_anomalies" in data
    assert "anomalies_by_type" in data
    assert "critical_anomalies" in data
