from __future__ import annotations

import os

import pytest

os.environ["MAC_ACCESS_API_KEY"] = "test-key-secure-1234"
os.environ["MAC_ACCESS_SCHEDULE_ENABLED"] = "false"

from mac_access_api.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

client = TestClient(app)
HEADERS = {"X-API-Key": "test-key-secure-1234"}


# ── Auth ─────────────────────────────────────────────────────────────────────

def test_health_no_key_allowed():
    r = client.get("/health")
    assert r.status_code == 200


def test_terminal_rejects_missing_key():
    r = client.post("/api/v1/terminal", json={"command": "echo hi"})
    assert r.status_code == 401


def test_terminal_rejects_wrong_key():
    r = client.post("/api/v1/terminal", headers={"X-API-Key": "wrong"}, json={"command": "echo hi"})
    assert r.status_code == 401
    assert r.headers.get("WWW-Authenticate") == "ApiKey"


# ── Terminal ─────────────────────────────────────────────────────────────────

def test_terminal_executes():
    r = client.post("/api/v1/terminal", headers=HEADERS, json={"command": "echo hello"})
    assert r.status_code == 200
    assert r.json()["stdout"].strip() == "hello"


def test_terminal_blocked_pattern():
    r = client.post("/api/v1/terminal", headers=HEADERS, json={"command": "rm -rf /"})
    assert r.status_code == 400


def test_terminal_empty_command_rejected():
    r = client.post("/api/v1/terminal", headers=HEADERS, json={"command": ""})
    assert r.status_code == 422


# ── Files ─────────────────────────────────────────────────────────────────────

def test_file_outside_allowed_blocked():
    r = client.post("/api/v1/files/read", headers=HEADERS, json={"path": "/etc/passwd"})
    assert r.status_code == 403


def test_file_write_and_read(tmp_path, monkeypatch):
    monkeypatch.setenv("MAC_ACCESS_ALLOWED_PATHS", str(tmp_path))
    import importlib
    import mac_access_api.config as cfg
    importlib.reload(cfg)
    import mac_access_api.services as svc
    importlib.reload(svc)

    test_file = str(tmp_path / "test.txt")
    r = client.post("/api/v1/files/write", headers=HEADERS,
                    json={"path": test_file, "content": "hello world"})
    assert r.status_code == 200

    r = client.post("/api/v1/files/read", headers=HEADERS, json={"path": test_file})
    assert r.status_code == 200
    assert r.json()["content"] == "hello world"


# ── Kill Switch ───────────────────────────────────────────────────────────────

def test_kill_switch_reset_requires_confirm():
    r = client.post("/api/v1/kill/reset", headers=HEADERS, json={"confirm": False})
    assert r.status_code == 400


# ── System ────────────────────────────────────────────────────────────────────

def test_system_info():
    r = client.get("/api/v1/system/info", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert "hostname" in data
    assert "macos_version" in data


def test_clipboard_get():
    r = client.get("/api/v1/clipboard", headers=HEADERS)
    assert r.status_code == 200
    assert "content" in r.json()


def test_audio_volume_get():
    r = client.get("/api/v1/audio/volume", headers=HEADERS)
    assert r.status_code == 200


def test_battery_info():
    r = client.get("/api/v1/system/battery", headers=HEADERS)
    assert r.status_code == 200
    assert "battery" in r.json()
