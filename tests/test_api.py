import os

os.environ["MAC_ACCESS_API_KEY"] = "change-me-now"

from fastapi.testclient import TestClient

from mac_access_api.main import app


client = TestClient(app)
AUTH = {"X-API-Key": "change-me-now"}


def test_health_rejects_without_key():
    response = client.get("/health")
    assert response.status_code == 401


def test_health_accepts_with_key():
    response = client.get("/health", headers=AUTH)
    assert response.status_code == 200


def test_terminal_executes_with_key():
    response = client.post(
        "/api/v1/terminal",
        headers=AUTH,
        json={"command": "echo hello"},
    )
    assert response.status_code == 200
    assert response.json()["stdout"].strip() == "hello"


def test_list_processes():
    response = client.get("/api/v1/mac/processes", headers=AUTH)
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["count"], int)
    assert isinstance(body["processes"], list)


def test_volume_payload_validation():
    response = client.post("/api/v1/mac/volume", headers=AUTH, json={"level": 200})
    assert response.status_code == 422


def test_kill_clear_endpoint_exists():
    response = client.post("/api/v1/kill/clear", headers=AUTH)
    assert response.status_code == 200


def test_message_notify_requires_key():
    response = client.post("/api/v1/messages/notify", json={"title": "t", "message": "m"})
    assert response.status_code == 401
