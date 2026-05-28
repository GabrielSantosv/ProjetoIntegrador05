"""
Tests for the JWT login flow.

Run with:
    c:/Users/joao.pedro/Desktop/ProjetoIntegrador05/.venv/Scripts/python.exe -m pytest tests/test_auth_system.py -v
"""

from __future__ import annotations

import os
import sys

from fastapi.testclient import TestClient

# Allow imports from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.auth_security import create_access_token, decode_access_token
from backend.main import app


def test_access_token_round_trip() -> None:
    token = create_access_token(7, "User@Example.com")
    payload = decode_access_token(token)

    assert payload["sub"] == "7"
    assert payload["email"] == "User@Example.com"
    assert "exp" in payload


def test_me_endpoint_requires_bearer_token() -> None:
    client = TestClient(app)

    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_me_endpoint_returns_current_user() -> None:
    client = TestClient(app)
    token = create_access_token(7, "User@Example.com")

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == {"id": 7, "email": "user@example.com"}