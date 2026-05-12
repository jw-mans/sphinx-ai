"""
Security tests:
  A) SQL-injection probes — all critical endpoints must handle payloads safely.
  B) Horizontal-privilege checks (REQ-SEC-02/04):
     - Unauthenticated requests to interview endpoints → 401.
     - Authenticated user A accessing user B's interview → 403.
"""
import pytest
from httpx import AsyncClient

# Common helpers

SQL_INJECTION_PAYLOADS = [
    "' OR '1'='1",
    "'; DROP TABLE users; --",
    "' UNION SELECT * FROM users --",
    "1; SELECT pg_sleep(5) --",
    "\\x27 OR 1=1 --",
    "<script>alert(1)</script>",
    "\" OR \"\"=\"",
]


async def _auth_user(client: AsyncClient, tg: str) -> tuple:
    """Create Telegram user and return (user_dict, jwt_token)."""
    r = await client.post("/auth/telegram", json={"telegram_id": tg, "name": "SecUser"})
    assert r.status_code == 200, r.text
    data = r.json()
    return data["user"], data["access_token"]


async def _make_user(client: AsyncClient, tg: str) -> dict:
    """Create user via legacy /users endpoint (no token returned)."""
    r = await client.post("/users", json={"telegram_id": tg})
    assert r.status_code == 200, r.text
    return r.json()


async def _start_interview(client: AsyncClient, user_id: int, token: str) -> int:
    r = await client.post(
        "/interview/start",
        json={"user_id": user_id, "level": "junior", "stack": "Python"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    return r.json()["interview_id"]

# A. SQL-injection probes

class TestSQLInjection:

    @pytest.mark.asyncio
    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
    async def test_create_user_sql_injection_in_telegram_id(self, client: AsyncClient, payload: str):
        """Injecting SQL via telegram_id must never cause 500."""
        r = await client.post("/users", json={"telegram_id": payload})
        assert r.status_code in (200, 400, 422), (
            f"Payload={payload!r} caused unexpected status {r.status_code}: {r.text}"
        )
        if r.status_code == 200:
            assert r.json()["telegram_id"] == payload, "ORM must store the raw string, not execute it as SQL"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
    async def test_get_user_sql_injection_in_path(self, client: AsyncClient, payload: str):
        """Injecting SQL in user_id path param must return 404 or 422 — never 500."""
        encoded = payload.replace("/", "%2F")
        r = await client.get(f"/users/{encoded}")
        assert r.status_code in (404, 422), (
            f"Payload={payload!r} gave unexpected status {r.status_code}"
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
    async def test_answer_sql_injection_in_text(self, client: AsyncClient, payload: str):
        """Injecting SQL via answer text must be stored safely and not cause 500."""
        user, token = await _auth_user(client, f"sqli_ans_{hash(payload) % 10**6}")
        iid = await _start_interview(client, user["id"], token)
        hdrs = {"Authorization": f"Bearer {token}"}

        r = await client.post(f"/interview/{iid}/answer", json={"text": payload}, headers=hdrs)
        assert r.status_code in (200, 400, 422), (
            f"Answer payload={payload!r} caused {r.status_code}: {r.text}"
        )

# B. Horizontal-privilege checks

class TestHorizontalPrivilege:

    @pytest.mark.asyncio
    async def test_unauthenticated_request_returns_401(self, client: AsyncClient):
        """REQ-SEC-01: All interview endpoints require a Bearer token."""
        assert (await client.get("/interview/1/question")).status_code == 401
        assert (await client.post("/interview/1/answer", json={"text": "x"})).status_code == 401
        assert (await client.get("/interview/1/result")).status_code == 401
        assert (await client.get("/interview/1/question/v2")).status_code == 401
        assert (await client.post("/interview/1/answer/v2", json={"text": "x"})).status_code == 401
        assert (await client.get("/interview/1/result/v2")).status_code == 401
        assert (await client.post("/interview/start", json={"user_id": 1, "level": "junior", "stack": "Python"})).status_code == 401

    @pytest.mark.asyncio
    async def test_user_a_cannot_get_user_b_question(self, client: AsyncClient):
        """REQ-SEC-02: User A with valid JWT gets 403 when reading user B's question."""
        user_a, token_a = await _auth_user(client, "priv_qa_new")
        user_b, token_b = await _auth_user(client, "priv_qb_new")

        iid_b = await _start_interview(client, user_b["id"], token_b)

        # User A uses their own valid token but targets user B's interview
        r = await client.get(
            f"/interview/{iid_b}/question",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"

    @pytest.mark.asyncio
    async def test_user_a_cannot_answer_user_b_interview(self, client: AsyncClient):
        """REQ-SEC-02: User A with valid JWT gets 403 when submitting to user B's interview."""
        user_a, token_a = await _auth_user(client, "priv_aa_new")
        user_b, token_b = await _auth_user(client, "priv_bb_new")

        iid_b = await _start_interview(client, user_b["id"], token_b)

        r = await client.post(
            f"/interview/{iid_b}/answer",
            json={"text": "Cross-user attack attempt"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"

    @pytest.mark.asyncio
    async def test_user_a_cannot_get_user_b_result(self, client: AsyncClient):
        """REQ-SEC-02: User A with valid JWT gets 403 when reading user B's result."""
        user_a, token_a = await _auth_user(client, "priv_ra_new")
        user_b, token_b = await _auth_user(client, "priv_rb_new")

        iid_b = await _start_interview(client, user_b["id"], token_b)
        await client.post(
            f"/interview/{iid_b}/answer",
            json={"text": "Some answer"},
            headers={"Authorization": f"Bearer {token_b}"},
        )

        r = await client.get(
            f"/interview/{iid_b}/result",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"

    @pytest.mark.asyncio
    async def test_user_a_cannot_get_user_b_question_v2(self, client: AsyncClient):
        """REQ-SEC-02: Same ownership check applies to v2 endpoints."""
        user_a, token_a = await _auth_user(client, "priv_v2_qa")
        user_b, token_b = await _auth_user(client, "priv_v2_qb")

        iid_b = await _start_interview(client, user_b["id"], token_b)

        r = await client.get(
            f"/interview/{iid_b}/question/v2",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_user_a_cannot_answer_v2_user_b_interview(self, client: AsyncClient):
        user_a, token_a = await _auth_user(client, "priv_v2_aa")
        user_b, token_b = await _auth_user(client, "priv_v2_bb")

        iid_b = await _start_interview(client, user_b["id"], token_b)

        r = await client.post(
            f"/interview/{iid_b}/answer/v2",
            json={"text": "attack"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_user_cannot_start_interview_for_another_user(self, client: AsyncClient):
        """REQ-SEC-03: user_id in /interview/start body must match JWT user_id."""
        user_a, token_a = await _auth_user(client, "priv_start_a")
        user_b, token_b = await _auth_user(client, "priv_start_b")

        # user_a tries to start an interview for user_b's account
        r = await client.post(
            "/interview/start",
            json={"user_id": user_b["id"], "level": "junior", "stack": "Python"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"

    @pytest.mark.asyncio
    async def test_user_cannot_read_other_users_profile(self, client: AsyncClient):
        """
        The /users/{id} endpoint is public (no auth) — but must return the
        correct user record without mixing in any other user's data.
        """
        user_a = await _make_user(client, "priv_a")
        user_b = await _make_user(client, "priv_b")

        r = await client.get(f"/users/{user_b['id']}")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == user_b["id"]
        assert data["telegram_id"] == user_b["telegram_id"]
        assert data["telegram_id"] != user_a["telegram_id"]
