"""
Tests for the /auth/* endpoints:
  - POST /auth/register
  - POST /auth/login
  - GET  /auth/me
  - POST /auth/telegram
"""
import pytest
from httpx import AsyncClient

# Helpers

_VALID_USER = {
    "email": "alice@example.com",
    "password": "secret123",
    "name": "Alice",
}


async def _register(client: AsyncClient, payload: dict = None) -> dict:
    payload = payload or _VALID_USER.copy()
    r = await client.post("/auth/register", json=payload)
    return r


async def _login(client: AsyncClient, email: str, password: str):
    return await client.post("/auth/login", json={"email": email, "password": password})

# POST /auth/register

async def test_register_returns_token_and_user(client: AsyncClient):
    r = await _register(client)
    assert r.status_code == 201, r.text
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    user = data["user"]
    assert user["email"] == _VALID_USER["email"]
    assert user["name"] == _VALID_USER["name"]
    assert "id" in user


async def test_register_duplicate_email_returns_409(client: AsyncClient):
    await _register(client)
    r = await _register(client)
    assert r.status_code == 409, r.text


async def test_register_invalid_email_returns_422(client: AsyncClient):
    r = await _register(client, {"email": "not-an-email", "password": "secret123", "name": "Bob"})
    assert r.status_code == 422, r.text


async def test_register_short_password_returns_422(client: AsyncClient):
    r = await _register(client, {"email": "bob@example.com", "password": "12345", "name": "Bob"})
    assert r.status_code == 422, r.text


async def test_register_missing_name_returns_422(client: AsyncClient):
    r = await client.post("/auth/register", json={"email": "bob@example.com", "password": "secret123"})
    assert r.status_code == 422, r.text


async def test_register_empty_name_returns_422(client: AsyncClient):
    r = await _register(client, {"email": "bob@example.com", "password": "secret123", "name": ""})
    assert r.status_code == 422, r.text

# POST /auth/login

async def test_login_success(client: AsyncClient):
    await _register(client)
    r = await _login(client, _VALID_USER["email"], _VALID_USER["password"])
    assert r.status_code == 200, r.text
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == _VALID_USER["email"]


async def test_login_wrong_password_returns_401(client: AsyncClient):
    await _register(client)
    r = await _login(client, _VALID_USER["email"], "wrongpassword")
    assert r.status_code == 401, r.text


async def test_login_wrong_email_returns_401(client: AsyncClient):
    await _register(client)
    r = await _login(client, "nobody@example.com", _VALID_USER["password"])
    assert r.status_code == 401, r.text


async def test_login_unregistered_user_returns_401(client: AsyncClient):
    r = await _login(client, "ghost@example.com", "password123")
    assert r.status_code == 401, r.text

# GET /auth/me

async def test_me_with_valid_token(client: AsyncClient):
    reg = await _register(client)
    token = reg.json()["access_token"]
    r = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["email"] == _VALID_USER["email"]


async def test_me_without_token_returns_401(client: AsyncClient):
    r = await client.get("/auth/me")
    assert r.status_code == 401, r.text


async def test_me_with_invalid_token_returns_401(client: AsyncClient):
    r = await client.get("/auth/me", headers={"Authorization": "Bearer this.is.garbage"})
    assert r.status_code == 401, r.text


async def test_me_with_malformed_header_returns_401(client: AsyncClient):
    r = await client.get("/auth/me", headers={"Authorization": "NotBearer sometoken"})
    assert r.status_code == 401, r.text


async def test_me_returns_same_data_as_register(client: AsyncClient):
    reg_data = (await _register(client)).json()
    token = reg_data["access_token"]
    me_data = (await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})).json()
    assert me_data["id"] == reg_data["user"]["id"]
    assert me_data["email"] == reg_data["user"]["email"]

# POST /auth/telegram

async def test_telegram_auth_creates_user(client: AsyncClient):
    r = await client.post("/auth/telegram", json={"telegram_id": "tg_12345", "name": "TgUser"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "access_token" in data
    user = data["user"]
    assert user["telegram_id"] == "tg_12345"
    assert user["name"] == "TgUser"


async def test_telegram_auth_is_idempotent(client: AsyncClient):
    payload = {"telegram_id": "tg_dup", "name": "DupUser"}
    r1 = await client.post("/auth/telegram", json=payload)
    r2 = await client.post("/auth/telegram", json=payload)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["user"]["id"] == r2.json()["user"]["id"]


async def test_telegram_auth_without_name(client: AsyncClient):
    r = await client.post("/auth/telegram", json={"telegram_id": "tg_noname"})
    assert r.status_code == 200, r.text
    assert "access_token" in r.json()


async def test_telegram_auth_token_works_for_me(client: AsyncClient):
    r = await client.post("/auth/telegram", json={"telegram_id": "tg_99", "name": "TgMe"})
    token = r.json()["access_token"]
    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["telegram_id"] == "tg_99"
