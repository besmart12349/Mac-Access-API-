from fastapi.testclient import TestClient

from mac_access_api.main import app


client = TestClient(app)


def test_health_rejects_without_key():
    response = client.get("/health")
    assert response.status_code == 401


def test_health_accepts_with_key():
    response = client.get("/health", headers={"X-API-Key": "change-me-now"})
    assert response.status_code == 200


def test_terminal_executes_with_key():
    response = client.post(
        "/api/v1/terminal",
        headers={"X-API-Key": "change-me-now"},
        json={"command": "echo hello"},
    )
    assert response.status_code == 200
    assert response.json()["stdout"].strip() == "hello"
