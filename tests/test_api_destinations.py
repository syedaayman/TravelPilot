"""
Phase 5 Tests: Destinations API
Validates listing, search, detail retrieval, and error handling for destinations.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_list_destinations(client: TestClient):
    response = client.get("/api/destinations")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "count" in data
    assert data["count"] >= 8
    names = [d["name"] for d in data["items"]]
    assert "Hyderabad" in names
    assert "Goa" in names
    assert "Jaipur" in names


def test_search_destinations(client: TestClient):
    response = client.get("/api/destinations?q=hyderabad")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 1
    assert data["items"][0]["name"] == "Hyderabad"

    # Search non-existent
    response2 = client.get("/api/destinations?q=atlantis_nowhere")
    assert response2.status_code == 200
    assert response2.json()["count"] == 0


def test_destination_details(client: TestClient):
    # Test lookup by ID or name
    response = client.get("/api/destinations/99852cd9-2775-52f3-8fe0-0a26c43a6c09")
    assert response.status_code == 200
    data = response.json()

    assert "destination" in data
    assert data["destination"]["name"] == "Hyderabad"
    assert "places" in data
    assert len(data["places"]) >= 3
    assert "hotels" in data
    assert len(data["hotels"]) >= 2
    assert "restaurants" in data
    assert len(data["restaurants"]) >= 2
    assert "transport_connections" in data


def test_unknown_destination(client: TestClient):
    response = client.get("/api/destinations/unknown-fake-id-999")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "DESTINATION_NOT_FOUND"
