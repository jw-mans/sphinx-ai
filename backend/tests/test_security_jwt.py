"""
Unit tests for core security utilities (no HTTP, no database):
  - hash_password / verify_password
  - create_access_token / decode_token
  - /auth/me endpoint with tampered / expired tokens
"""
import time
from datetime import timedelta, datetime, timezone

import pytest
from jose import jwt

from src.app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
)
from src.app.config import settings

# hash_password / verify_password

class TestPasswordHashing:
    def test_hash_differs_from_plain(self):
        hashed = hash_password("mysecret")
        assert hashed != "mysecret"

    def test_verify_correct_password(self):
        hashed = hash_password("correcthorse")
        assert verify_password("correcthorse", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("correcthorse")
        assert verify_password("wronghorse", hashed) is False

    def test_hashes_are_salted(self):
        """Same password must produce different hashes (bcrypt salting)."""
        h1 = hash_password("password")
        h2 = hash_password("password")
        assert h1 != h2

    def test_empty_password_can_be_hashed_and_verified(self):
        hashed = hash_password("")
        assert verify_password("", hashed) is True
        assert verify_password("notempty", hashed) is False

    def test_unicode_password(self):
        pw = "пароль123!@#"
        hashed = hash_password(pw)
        assert verify_password(pw, hashed) is True
        assert verify_password("wrong", hashed) is False

# create_access_token / decode_token

class TestJWT:
    def test_decode_token_returns_correct_user_id(self):
        token = create_access_token(42)
        assert decode_token(token) == 42

    def test_decode_token_returns_none_for_garbage(self):
        assert decode_token("this.is.garbage") is None

    def test_decode_token_returns_none_for_empty_string(self):
        assert decode_token("") is None

    def test_decode_token_returns_none_for_tampered_payload(self):
        token = create_access_token(1)
        # Tamper: replace signature segment
        parts = token.split(".")
        tampered = parts[0] + "." + parts[1] + ".invalidsignature"
        assert decode_token(tampered) is None

    def test_decode_token_returns_none_for_wrong_secret(self):
        """Token signed with a different secret must be rejected."""
        fake_token = jwt.encode(
            {"sub": "99", "exp": datetime.now(timezone.utc) + timedelta(days=1)},
            "completely-different-secret",
            algorithm=settings.JWT_ALGORITHM,
        )
        assert decode_token(fake_token) is None

    def test_token_encodes_user_id_as_string_sub(self):
        """JWT payload 'sub' must be a string representation of the user ID."""
        token = create_access_token(7)
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        assert payload["sub"] == "7"

    def test_token_has_exp_claim(self):
        token = create_access_token(1)
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        assert "exp" in payload

    def test_token_expiry_is_in_future(self):
        token = create_access_token(1)
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        assert exp > datetime.now(timezone.utc)

    def test_different_users_get_different_tokens(self):
        t1 = create_access_token(1)
        t2 = create_access_token(2)
        assert t1 != t2

    def test_large_user_id_round_trips(self):
        token = create_access_token(2**31 - 1)
        assert decode_token(token) == 2**31 - 1

# /auth/me — token validation via HTTP

class TestAuthMeTokenValidation:
    async def test_valid_token_accepted(self, client):
        # Register first to get a real token
        r = await client.post("/auth/register", json={
            "email": "jwt_test@example.com",
            "password": "secret123",
            "name": "JwtUser",
        })
        assert r.status_code == 201
        token = r.json()["access_token"]
        me = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200

    async def test_garbage_token_returns_401(self, client):
        r = await client.get("/auth/me", headers={"Authorization": "Bearer garbage.token.here"})
        assert r.status_code == 401

    async def test_no_token_returns_401(self, client):
        r = await client.get("/auth/me")
        assert r.status_code == 401

    async def test_token_signed_with_wrong_secret_returns_401(self, client):
        fake_token = jwt.encode(
            {"sub": "1", "exp": datetime.now(timezone.utc) + timedelta(days=1)},
            "wrong-secret",
            algorithm="HS256",
        )
        r = await client.get("/auth/me", headers={"Authorization": f"Bearer {fake_token}"})
        assert r.status_code == 401

    async def test_token_for_nonexistent_user_returns_401_or_404(self, client):
        """A valid token for a user that was deleted (or never existed) must be rejected."""
        token = create_access_token(999999)
        r = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        # 404 if user not found, 401 if invalid token — either is acceptable
        assert r.status_code in (401, 404)
